import { oauthClient } from '@/auth-client.js';
import { Request, Response } from 'express';

export const googleAuth = (req: Request, res: Response) => {
  const url = oauthClient.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',
    scope: ['openid', 'profile', 'email'],
  });
    
    res.redirect(url)
};
