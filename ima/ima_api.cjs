#!/usr/bin/env node
'use strict';
/*
 * ima_api.cjs — IMA OpenAPI 统一调用入口（按官方 v1.1.10 安装指南契约重建）
 *
 * 用法：
 *   node ima_api.cjs "<API路径>" '<JSON请求体>' [OPTS]
 *   node ima_api.cjs "openapi/wiki/v1/search_knowledge_base" '{"query":""}'
 *
 * OPTS（可选，第三参数，适合不便写用户目录的沙盒）：
 *   '{"clientId":"...","apiKey":"..."}'  （也接受 client_id/api_key 键名）
 *
 * 凭证优先级：
 *   1. OPTS 参数
 *   2. 环境变量 IMA_CLIENT_ID / IMA_API_KEY
 *   3. 环境变量 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY
 *   4. 配置文件 ~/.config/ima/client_id 与 ~/.config/ima/api_key
 *   5. $IMA_CREDENTIALS_FILE 指向的 JSON 文件（clientId/apiKey 或 client_id/api_key）
 *
 * 约定：
 *   - Base URL: https://ima.qq.com（所有请求仅发往官方域名）
 *   - 认证头：ima-openapi-clientid / ima-openapi-apikey
 *   - 统一响应：{"code":0,"msg":"...","data":{...}}；code=-200 表示技能有新版本
 *   - 凭证仅发往 ima.qq.com，不写入日志、不外传
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const BASE_URL = 'https://ima.qq.com';

function fromPair(clientId, apiKey, from) {
  if (clientId && apiKey) return { clientId, apiKey, from };
  return null;
}

function loadCredentials() {
  // 1. OPTS 参数
  const optsRaw = process.argv[4];
  if (optsRaw) {
    try {
      const o = JSON.parse(optsRaw);
      const hit = fromPair(o.clientId, o.apiKey, 'opts') || fromPair(o.client_id, o.api_key, 'opts');
      if (hit) return hit;
    } catch (e) {
      console.error('OPTS 第三参数不是合法 JSON：' + e.message);
      process.exit(2);
    }
  }
  // 2/3. 环境变量
  const envHit = fromPair(process.env.IMA_CLIENT_ID, process.env.IMA_API_KEY, 'env:IMA_*')
    || fromPair(process.env.IMA_OPENAPI_CLIENTID, process.env.IMA_OPENAPI_APIKEY, 'env:IMA_OPENAPI_*');
  if (envHit) return envHit;
  // 4. 配置文件
  try {
    const dir = path.join(os.homedir(), '.config', 'ima');
    const clientId = fs.readFileSync(path.join(dir, 'client_id'), 'utf8').trim();
    const apiKey = fs.readFileSync(path.join(dir, 'api_key'), 'utf8').trim();
    const fileHit = fromPair(clientId, apiKey, 'file:~/.config/ima');
    if (fileHit) return fileHit;
  } catch (e) { /* 未配置，继续 */ }
  // 5. IMA_CREDENTIALS_FILE
  if (process.env.IMA_CREDENTIALS_FILE) {
    try {
      const o = JSON.parse(fs.readFileSync(process.env.IMA_CREDENTIALS_FILE, 'utf8'));
      const credHit = fromPair(o.clientId, o.apiKey, 'file:$IMA_CREDENTIALS_FILE')
        || fromPair(o.client_id, o.api_key, 'file:$IMA_CREDENTIALS_FILE');
      if (credHit) return credHit;
    } catch (e) {
      console.error('IMA_CREDENTIALS_FILE 读取失败：' + e.message);
      process.exit(2);
    }
  }
  return null;
}

async function main() {
  const apiPath = process.argv[2];
  if (!apiPath || apiPath === '--help' || apiPath === '-h') {
    console.log('用法: node ima_api.cjs "<API路径>" \'<JSON请求体>\' [OPTS]');
    console.log('示例: node ima_api.cjs "openapi/wiki/v1/search_knowledge_base" \'{"query":""}\'');
    process.exit(apiPath ? 0 : 2);
  }
  const bodyRaw = process.argv[3] || '{}';
  let bodyObj;
  try {
    bodyObj = JSON.parse(bodyRaw);
  } catch (e) {
    console.error('请求体不是合法 JSON：' + e.message);
    process.exit(2);
  }

  const cred = loadCredentials();
  if (!cred) {
    console.error('缺少 IMA 凭证。请按 SKILL.md Setup 配置：OPTS 参数 / 环境变量 / ~/.config/ima/ / $IMA_CREDENTIALS_FILE');
    process.exit(1);
  }

  const url = BASE_URL + '/' + apiPath.replace(/^\/+/, '');
  let resp;
  try {
    resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ima-openapi-clientid': cred.clientId,
        'ima-openapi-apikey': cred.apiKey,
      },
      body: JSON.stringify(bodyObj),
    });
  } catch (e) {
    console.error('请求失败（网络层）：' + e.message);
    process.exit(1);
  }

  const text = await resp.text();
  let out;
  try {
    out = JSON.parse(text);
  } catch (e) {
    out = { http_status: resp.status, raw: text.slice(0, 2000) };
  }
  console.log(JSON.stringify(out));
  if (out && typeof out.code === 'number' && out.code !== 0) process.exit(1);
}

main();
