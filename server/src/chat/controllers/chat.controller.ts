import { askLLM } from '@/utils/askLLM.js';
import { retrieveRelevant } from '@/utils/retriveRelevant.js';
import { Request, Response } from 'express';


export async function RAGChat(req: Request, res: Response) {
  try {
    const { message, legalArea } = req.body;
    const file = req.file;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    let context = '';
    if (file) {
      //    const parsedText = await parseDocument(file);

      //    // delete file immediately after reading
      //    fs.unlinkSync(file.path);

      //    await storeEmbeddings(parsedText, legalArea);

      //    context = await retrieveRelevant(message, legalArea);
      //
      return;
    }
    // 🔥 CASE 2: WITHOUT FILE
    else {
      context = await retrieveRelevant({query: message, legalArea});
    }

    const response = await askLLM(message, context);

    return res.json({
      success: true,
      data: response,
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      message: `[RAG CHAT]: INTERNAL SERVER ERROR`,
    });
  }
}
