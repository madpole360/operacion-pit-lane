/**
 * Cloudflare Worker — Dispara el workflow de Operación Pit-Lane
 * vía GitHub API repository_dispatch.
 *
 * Configuración necesaria en Cloudflare:
 *   1. Variables de entorno: GITHUB_TOKEN, GITHUB_REPO
 *   2. Cron trigger: 0 18 * * 1,4 (lunes y jueves 18:00 UTC = 20:00 Madrid)
 *
 * Para probarlo manualmente: visita la URL del worker.
 */

export default {
  async scheduled(event, env, ctx) {
    await dispatchWorkflow(env);
  },

  async fetch(request, env, ctx) {
    // Permitir disparo manual visitando la URL
    await dispatchWorkflow(env);
    return new Response(JSON.stringify({ ok: true, time: new Date().toISOString() }), {
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

async function dispatchWorkflow(env) {
  const token = env.GITHUB_TOKEN;
  const repo = env.GITHUB_REPO || 'madpole360/operacion-pit-lane';

  if (!token) {
    console.error('GITHUB_TOKEN no configurado');
    return;
  }

  const response = await fetch(
    `https://api.github.com/repos/${repo}/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'User-Agent': 'operacion-pit-lane',
        'Accept': 'application/vnd.github+json',
      },
      body: JSON.stringify({
        event_type: 'scheduled-run',
      }),
    }
  );

  if (response.ok) {
    console.log(`Workflow disparado: ${response.status}`);
  } else {
    const text = await response.text();
    console.error(`Error ${response.status}: ${text}`);
  }
}
