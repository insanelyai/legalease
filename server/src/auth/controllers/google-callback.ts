import { oauthClient } from '@/auth-client.js';
import { env } from '@/config/env.js';
import { prisma } from '@/libs/prisma.js';
import { createJwt } from '@/utils/create-jwt.js';
import { Request, Response } from 'express';

export const googleCallback = async (req: Request, res: Response) => {
  const code = req.query.code as string;

  if (!code) {
    return res.status(400).send('Missing code');
  }

  const { tokens } = await oauthClient.getToken(code);
  oauthClient.setCredentials(tokens);

  const ticket = await oauthClient.verifyIdToken({
    idToken: tokens.id_token!,
    audience: env.GOOGLE_CLIENT_ID,
  });

  const payload = ticket.getPayload();

  if (!payload?.sub) {
    return res.status(400).send('Invalid Google Payload');
  }

  const userData = {
    isGoogle: true,
    email: payload.email,
    name: payload.name,
    picture: payload.picture,
  };
    
  if (!userData.email || !userData.name) {
    throw new Error('Missing required fields');
  }

  const user = await prisma.user.create({
    data: {
      email: userData.email,
      name: userData.name,
      picture: userData.picture,
      isGoogle: true,
    },
  });

  const jwt = createJwt({
    id: user.id,
    email: user.email,
  });

  res.cookie('session', jwt, {
    httpOnly: true,
    sameSite: 'lax',
    secure: false,
    maxAge: 2 * 60 * 60 * 1000,
  });

  res.redirect(`${env.FRONTEND_URL}/dashboard`);
};
