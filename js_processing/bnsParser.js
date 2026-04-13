import { PDFParse } from "pdf-parse";
import fs from "fs";
import axios from "axios";
import pLimit from "p-limit";

const limit = pLimit(1); // control concurrency
const OUTPUT_DIR = "./output";

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR);
}

function getSectionFilePath(sectionNum) {
    return `${OUTPUT_DIR}/section_${sectionNum}.json`;
}

function isSectionProcessed(sectionNum) {
    return fs.existsSync(getSectionFilePath(sectionNum));
}

function saveSection(sectionNum, data) {
    fs.writeFileSync(
        getSectionFilePath(sectionNum),
        JSON.stringify(data, null, 2)
    );
}


const PROGRESS_FILE = "./bns.progress.json";
const OUTPUT_FILE = "./bns.json";

function loadProgress() {
    if (!fs.existsSync(PROGRESS_FILE)) {
        return { processedSections: [] };
    }
    return JSON.parse(fs.readFileSync(PROGRESS_FILE, "utf-8"));
}

function saveProgress(progress) {
    fs.writeFileSync(PROGRESS_FILE, JSON.stringify(progress, null, 2));
}

function appendChunks(chunks) {
    let existing = [];

    if (fs.existsSync(OUTPUT_FILE)) {
        existing = JSON.parse(fs.readFileSync(OUTPUT_FILE, "utf-8"));
    }

    const updated = [...existing, ...chunks];

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(updated, null, 2));
}

// ---------------- PDF ----------------
export async function extractPdfText(filePath) {
    const parser = new PDFParse({ url: filePath });
    const result = await parser.getText();
    return result.text;
}

// ---------------- CLEAN ----------------
export function cleanText(text) {
    return text
        .replace(/\n{2,}/g, "\n")
        .replace(/([a-z])\n([a-z])/g, "$1 $2")
        .replace(/\n\d+\n/g, "\n")
        .replace(/[ \t]+/g, " ")
        .trim();
}

// ---------------- SPLIT ----------------
function splitSections(text) {
    const parts = text.split(/(?=\n\s*\d+\.\s+)/g);
    return parts.filter(p => p.trim().length > 100);
}

// ---------------- META ----------------
function extractSectionMeta(sectionText) {
    const match = sectionText.match(/\n?\s*(\d+)\.\s+([^\n]+)/);

    return {
        section_num: match?.[1] || null,
        section_title: match?.[2]?.trim() || null
    };
}

// ---------------- REFS ----------------
function extractRefs(text) {
    return text.match(/Section\s+\d+/g) || [];
}

// ---------------- SAFE JSON ----------------
function safeJsonParse(str) {
    try {
        return JSON.parse(str);
    } catch {
        return null;
    }
}

// ---------------- LLM ----------------
const CHUNK_PROMPT = `
You are parsing Indian legal text.

Break into:
- main rule
- clauses (a, b, c)
- explanations
- illustrations

Return JSON:
[
  {
    "chunk_type": "main_rule | clause | explanation | illustration | punishment",
    "text": "",
    "clause": "(a)/(b)/null",
    "cross_refs": []
  }
]

Return ONLY JSON.
`;

async function chunkWithLLM(text) {
    const res = await axios.post("http://localhost:1234/v1/chat/completions", {
        model: "qwen2.5-7b-instruct",
        messages: [
            { role: "system", content: "You output strict JSON only." },
            { role: "user", content: CHUNK_PROMPT + text.slice(0, 6000) } // limit size
        ],
        temperature: 0.1
    });

    return res.data.choices[0].message.content;
}

// ---------------- RETRY ----------------
async function chunkWithRetry(text, retries = 2) {
    for (let i = 0; i <= retries; i++) {
        const res = await chunkWithLLM(text);
        const parsed = safeJsonParse(res);

        if (parsed) return parsed;

        console.log("Retrying LLM JSON fix...");
        text = `Fix this JSON and return valid JSON only:\n${res}`;
    }

    return null;
}

// ---------------- MAIN ----------------
async function processBNS(pdfPath) {
    const raw = await extractPdfText(pdfPath);
    const cleaned = cleanText(raw);
    const sections = splitSections(cleaned);

    console.log(`Total sections: ${sections.length}`);

    for (const section of sections) {
        const meta = extractSectionMeta(section);

        if (!meta.section_num) continue;

        const sectionNum = meta.section_num;

        // 🔥 SKIP if already done
        if (isSectionProcessed(sectionNum)) {
            console.log(`Skipping section ${sectionNum}`);
            continue;
        }

        console.log(`Processing section ${sectionNum}`);

        const parsed = await chunkWithRetry(section);

        if (!parsed) {
            console.log(`❌ Failed section ${sectionNum}`);
            continue;
        }

        const enriched = parsed.map((c, i) => ({
            ...c,
            ...meta,
            chunk_index: i,
            cross_refs: extractRefs(c.text),
            word_count: c.text.split(" ").length
        }));

        // ✅ Save per section
        saveSection(sectionNum, enriched);

        console.log(`✅ Saved section ${sectionNum}`);
    }

    console.log("Done");
}
// ---------------- RUN ----------------
processBNS("./bns/Bharatiya Nyaya Sanhita, 2023.pdf")
    .then(() => console.log("Done"))
    .catch(console.error);