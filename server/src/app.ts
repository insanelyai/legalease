import { requestLogger } from './logger.middleware.js';
import express, { Application } from 'express';
import { Pool } from 'pg';
import cors from 'cors';

import appRouter from './index.router.js';

const app: Application = express();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(requestLogger);

export const db = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

app.use('/api', appRouter);

export default app;
