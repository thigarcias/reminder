require('dotenv').config();

const apiKey = process.env.CRON_JOB_API_KEY;
const jobId = 8181044;

async function updateUrl(newUrl) {
  if (!apiKey) {
    console.error('❌ Erro: CRON_JOB_API_KEY não encontrada no arquivo .env');
    return;
  }

  if (!newUrl) {
    console.log('Uso: node scripts/update-cron-url.js https://seu-app.vercel.app/api/cron');
    return;
  }

  const cleanUrl = newUrl.endsWith('/api/cron') ? newUrl : `${newUrl.replace(/\/$/, '')}/api/cron`;

  console.log(`Atualizando Cron Job #${jobId} no cron-job.org para a URL: ${cleanUrl}...`);

  const res = await fetch(`https://api.cron-job.org/jobs/${jobId}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      job: {
        url: cleanUrl,
        enabled: true,
      }
    })
  });

  if (res.ok) {
    console.log('✅ Cron Job atualizado com sucesso no cron-job.org!');
  } else {
    console.error('❌ Erro ao atualizar Cron Job:', await res.text());
  }
}

const targetUrl = process.argv[2];
updateUrl(targetUrl);
