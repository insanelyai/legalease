import { spawn } from 'child_process';
import readline from 'readline';

const py = spawn('python3', ['embed_server.py']);

const rl = readline.createInterface({
  input: py.stdout,
});

type Pending = {
  resolve: (v: number[]) => void;
  reject: (e: unknown) => void;
};

const queue: Pending[] = [];

rl.on('line', (line) => {
  const trimmed = line.trim();

  if (!trimmed.startsWith('[')) return; // ignore logs

  const current = queue.shift();
  if (!current) return;

  try {
    const embedding = JSON.parse(trimmed);
    current.resolve(embedding);
  } catch (err) {
    current.reject(err);
  }
});

export function getEmbedding(text: string): Promise<number[]> {
  return new Promise((resolve, reject) => {
    console.log('[EMBEDDING...]');

    queue.push({ resolve, reject });
    py.stdin.write(text + '\n');
  });
}
