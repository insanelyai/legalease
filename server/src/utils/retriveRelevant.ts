import { db } from '@/app.js';
import { getEmbedding } from './getEmbedding.js';

type RetrieveParams = {
  query: string;
  legalArea?: string;
  limit?: number;
};

type Row = { text: string };

function toPgVector(embedding: number[]): string {
  return `[${embedding.join(',')}]`;
}

export async function retrieveRelevant({
  query,
  legalArea,
  limit = 12,
}: RetrieveParams): Promise<string> {
  if (!query?.trim()) return '';

  // 1. Generate embedding
  const embedding = await getEmbedding(query);

  const vector = toPgVector(embedding);

  if (!embedding || !embedding.length) {
    throw new Error('Embedding generation failed');
  }

  // 2. Run hybrid search
  const result = await db.query(
    `
    SELECT 
      text,
      embedding <-> $1::vector AS vector_score,
      ts_rank(fts, plainto_tsquery($2)) AS text_score
    FROM legal_chunks
    WHERE ($3::text IS NULL OR law_type = $3)
      AND embedding IS NOT NULL
    ORDER BY vector_score ASC, text_score DESC
    LIMIT $4
    `,
    [vector, query, legalArea ?? null, limit]
  );

  // 3. Clean + format output
  const rows = result.rows ?? [];

  if (!rows.length) return '';

  return rows
    .map((r: Row, i: number) => {
      const cleaned = r.text?.trim().replace(/\s+/g, ' ');
      return `#${i + 1}\n${cleaned}`;
    })
    .join('\n\n---\n\n');
}
