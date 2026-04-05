import { Router } from 'express';
import authRoutes from '@/auth/routes/auth.route.js';
import chatRoutes from '@/chat/routes/chat.route.js';

const router = Router();

router.use('/auth', authRoutes);
router.use('/chat', chatRoutes);

export default router;
