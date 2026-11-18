import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const MOCK_REACT_NATIVE = pathToFileURL(path.resolve('./scripts/mock-react-native.mjs')).href;
const MOCK_EMPTY = pathToFileURL(path.resolve('./scripts/mock-empty.mjs')).href;

export async function resolve(specifier, context, nextResolve) {
  if (specifier === 'react-native') {
    return {
      format: 'module',
      shortCircuit: true,
      url: MOCK_REACT_NATIVE,
    };
  }

  if (specifier === 'expo-constants' || specifier.startsWith('expo-modules-core')) {
    return {
      format: 'module',
      shortCircuit: true,
      url: MOCK_EMPTY,
    };
  }

  try {
    return await nextResolve(specifier, context);
  } catch (err) {
    if (err.code === 'ERR_MODULE_NOT_FOUND' || err.code === 'ERR_UNSUPPORTED_DIR_IMPORT') {
      if (specifier.startsWith('.') || specifier.startsWith('/')) {
        const parentDir = context.parentURL ? path.dirname(fileURLToPath(context.parentURL)) : process.cwd();
        const target = path.resolve(parentDir, specifier);
        for (const ext of ['.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.js']) {
          if (fs.existsSync(target + ext)) {
            return nextResolve(pathToFileURL(target + ext).href, context);
          }
        }
      } else {
        for (const ext of ['.js', '.mjs', '/index.js']) {
          try {
            return await nextResolve(specifier + ext, context);
          } catch {}
        }
      }
    }
    throw err;
  }
}

export async function load(url, context, nextLoad) {
  if (url.endsWith('.tsx') || url.endsWith('.jsx')) {
    const filePath = fileURLToPath(url);
    const source = fs.readFileSync(filePath, 'utf8');
    const { default: ts } = await import('typescript');
    const transpiled = ts.transpileModule(source, {
      compilerOptions: {
        jsx: ts.JsxEmit.ReactJSX,
        module: ts.ModuleKind.ESNext,
        target: ts.ScriptTarget.ESNext,
      },
      fileName: filePath,
    });
    return {
      format: 'module',
      shortCircuit: true,
      source: transpiled.outputText,
    };
  }
  return nextLoad(url, context);
}
