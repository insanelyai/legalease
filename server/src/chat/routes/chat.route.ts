import { upload } from '@/utils/multer.handler.js';
import { Router } from 'express';
import { RAGChat } from '../controllers/chat.controller.js';

const router = Router();

router.post('/rag', upload.single('file'), RAGChat);

export default router;
