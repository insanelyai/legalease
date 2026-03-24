import { Request, Response, Router } from 'express';

const router = Router();


// @route   GET /health
// @desc    Health check endpoint
// @access  Public

router.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK' });
});

export default router;
