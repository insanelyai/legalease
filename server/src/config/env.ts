import dotenv from 'dotenv';
dotenv.config();

const required = ['PORT'];

required.forEach((key) => {
  if (!process.env[key]) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
});

export const env = {
  PORT: Number(process.env.PORT),
  NODE_ENV: process.env.NODE_ENV || 'development',
};
