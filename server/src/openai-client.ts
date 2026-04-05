import OpenAI from 'openai';

export const aiClient = new OpenAI({
  baseURL: 'http://localhost:1234/v1',
    apiKey: 'lm-studio',
  
});
