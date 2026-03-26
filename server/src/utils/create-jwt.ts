import { env } from '@/config/env.js';
import jwt from 'jsonwebtoken';

export function createJwt(user: unknown) {
  return jwt.sign({ user }, env.GOOGLE_CLIENT_SECRET!, {
    expiresIn: '2h',
  });
}
