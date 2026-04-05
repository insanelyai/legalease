import { aiClient } from '@/openai-client.js';

export async function askLLM(message: string, context: string) {
  console.log(context);
  const completion = await aiClient.chat.completions.create({
    model: 'local-model',
    messages: [
      {
        role: 'system',
        content: `You are a legal assistant.

Use ONLY the information provided in the context below to answer the question.

Context:
${context}

Strict Rules:
- Do NOT use any external knowledge.
- Do NOT infer, assume, or interpret beyond the given context.
- Do NOT mix BNS with IPC under any circumstances.
- Do NOT mention IPC unless it explicitly appears in the context.
- Do NOT generate or reference any legal sections that are not present in the context.

Answer concisely and accurately, strictly based on the context.

            `,
      },
      {
        role: 'user',
        content: message,
      },
    ],
    temperature: 0.2,
  });

  return completion.choices[0].message.content;
}
