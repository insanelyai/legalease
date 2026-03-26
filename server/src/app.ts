import { requestLogger } from './middleware/logger.middleware.js';
import express, { Application } from 'express';
import cors from 'cors';

import appRouter from './index.router.js';

const app: Application = express();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(requestLogger);

app.use('/api', appRouter);

export default app;
