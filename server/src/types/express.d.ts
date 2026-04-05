import { JwtPayload } from 'jsonwebtoken';

declare global {
  namespace Express {
    interface Request {
      user?: JwtPayload | unknown;
      file?: Express.Multer.File;
    }
  }
}

export {};
