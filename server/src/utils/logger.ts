import pino from 'pino';
import path from 'path';
import fs from 'fs';

const logsDir = path.join(process.cwd(), 'logs');
if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir);

const logger = pino({
  level: 'info',
  transport: {
    targets: [
      {
        target: 'pino-pretty',
        options: { colorize: true },
        level: 'info',
      },
      {
        target: 'pino/file',
        options: { destination: `${logsDir}/app.log` },
        level: 'info',
      },
      {
        target: 'pino/file',
        options: { destination: `${logsDir}/error.log` },
        level: 'error',
      },
    ],
  },
});

export default logger;
