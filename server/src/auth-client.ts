import { OAuth2Client } from 'google-auth-library';
import { env } from './config/env.js';

export const oauthClient = new OAuth2Client({
  client_id: env.GOOGLE_CLIENT_ID,
  client_secret: env.GOOGLE_CLIENT_SECRET,
  redirectUri: env.CALLBACK_URL,
});
