import { createServer } from 'node:http';
import { request as httpRequest } from 'node:http';

const BACKEND_PORT = 5000;
const PORT = parseInt(process.env.PORT || '7860', 10);

async function main() {
  const { default: serverHandler, renderErrorPage } = await import('./dist/server/server.js');

  const server = createServer(async (req, res) => {
    if (req.url.startsWith('/api/')) {
      const proxyReq = httpRequest(
        {
          hostname: '127.0.0.1',
          port: BACKEND_PORT,
          path: req.url,
          method: req.method,
          headers: { ...req.headers, host: `127.0.0.1:${BACKEND_PORT}` },
        },
        (proxyRes) => {
          res.writeHead(proxyRes.statusCode, proxyRes.headers);
          proxyRes.pipe(res);
        },
      );
      req.pipe(proxyReq);
      proxyReq.on('error', (err) => {
        console.error('Proxy error:', err);
        res.writeHead(502, { 'Content-Type': 'text/plain' });
        res.end('Bad Gateway');
      });
      return;
    }

    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const body = Buffer.concat(chunks).toString() || undefined;

    const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
    const request = new Request(url, {
      method: req.method,
      headers: req.headers,
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : body,
    });

    try {
      const response = await serverHandler.fetch(request, {}, {});
      res.writeHead(response.status, Object.fromEntries(response.headers));
      res.end(await response.text());
    } catch (err) {
      console.error('SSR error:', err);
      if (renderErrorPage) {
        res.writeHead(500, { 'Content-Type': 'text/html' });
        res.end(renderErrorPage());
      } else {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Internal Server Error');
      }
    }
  });

  server.listen(PORT, '0.0.0.0', () => {
    console.log(`Frontend SSR server listening on http://0.0.0.0:${PORT}`);
  });
}

main().catch(console.error);
