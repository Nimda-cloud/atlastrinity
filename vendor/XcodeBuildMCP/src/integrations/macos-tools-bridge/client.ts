// DEPRECATED: This file is superseded by backend.ts
// Kept as a re-export shim for backward compatibility.
// All new code should import from backend.ts or index.ts directly.
export {
  BridgeBackend as MacOSToolsBridgeClient,
  type BridgeBackendStatus as MacOSToolsBridgeClientStatus,
  type BridgeBackendConfig as MacOSToolsBridgeClientOptions,
} from './backend.ts';
