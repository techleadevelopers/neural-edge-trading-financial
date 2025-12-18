import { z } from 'zod';
import { insertSignalSchema, signals, alerts } from './schema';

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

export const api = {
  signals: {
    list: {
      method: 'GET' as const,
      path: '/api/signals',
      input: z.object({
        minScore: z.coerce.number().optional(),
        onlyStrong: z.coerce.boolean().optional(),
      }).optional(),
      responses: {
        200: z.array(z.custom<typeof signals.$inferSelect>()),
      },
    },
    get: {
      method: 'GET' as const,
      path: '/api/signals/:id',
      responses: {
        200: z.custom<typeof signals.$inferSelect>(),
        404: errorSchemas.notFound,
      },
    },
    latest: {
      method: 'GET' as const,
      path: '/api/signals/latest',
      responses: {
        200: z.custom<{ lastUpdate: string }>(),
      }
    }
  },
  alerts: {
    list: {
      method: 'GET' as const,
      path: '/api/alerts',
      responses: {
        200: z.array(z.custom<typeof alerts.$inferSelect>()),
      },
    },
  }
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}
