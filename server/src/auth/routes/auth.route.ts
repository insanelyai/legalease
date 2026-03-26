import { Router } from 'express';
import { googleAuth } from '../controllers/google-auth.js';
import { googleCallback } from '../controllers/google-callback.js';

const router = Router();

router.get('/google', googleAuth);
router.get('/callback/google', googleCallback);

export default router;
