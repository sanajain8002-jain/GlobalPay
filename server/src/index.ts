/**
 * GlobalPay 2.0 Express + TypeScript Entry Point
 * Mounts versioned REST API under /api/v1 with Helmet, CORS, Rate Limiting,
 * Request ID correlation, CSRF verification, and Centralized Error Handling.
 */
import { loadAndValidateConfig } from "./config/env.js";
import { createHttpServer, GlobalPayEngine } from "./runtime.mjs";

const config = loadAndValidateConfig(process.env);
const engine = new GlobalPayEngine({
  webhookSecret: config.paymentWebhookSecret,
});

const { server } = createHttpServer(engine);

server.listen(config.port, () => {
  console.log(
    JSON.stringify({
      level: "info",
      event: "SERVER_STARTED",
      port: config.port,
      apiPrefix: config.apiPrefix,
      environment: config.nodeEnv,
      providerMode: config.paymentProviderMode,
      timestamp: new Date().toISOString(),
    })
  );
});
