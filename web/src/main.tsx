import React from 'react'
import { createRoot } from 'react-dom/client'
import { Amplify } from 'aws-amplify'
import 'aws-amplify/auth/enable-oauth-listener'
import App from './App'
import type { AppConfig } from './types'
import './style.css'

async function start() {
  const response = await fetch('/config.json', { cache: 'no-store' })
  const config = (await response.json()) as AppConfig
  if (!config.userPoolId || !config.redirectUrl) throw new Error('App authentication is not configured')
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.userPoolId,
        userPoolClientId: config.userPoolClientId,
        loginWith: {
          oauth: {
            domain: config.cognitoDomain,
            scopes: ['openid', 'email'],
            redirectSignIn: [config.redirectUrl],
            redirectSignOut: [config.redirectUrl],
            responseType: 'code',
          },
        },
      },
    },
  })
  createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
}

start().catch((error: unknown) => {
  document.getElementById('root')!.textContent = error instanceof Error ? error.message : 'Could not start the app'
})
