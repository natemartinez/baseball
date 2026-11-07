// React Native / Hermes Polyfills for 3D & Web libraries
if (typeof (globalThis as unknown as { DOMRect: unknown }).DOMRect === 'undefined') {
  class DOMRect {
    x = 0;
    y = 0;
    width = 0;
    height = 0;
    top = 0;
    right = 0;
    bottom = 0;
    left = 0;
    constructor(x = 0, y = 0, width = 0, height = 0) {
      this.x = x;
      this.y = y;
      this.width = width;
      this.height = height;
      this.top = y;
      this.right = x + width;
      this.bottom = y + height;
      this.left = x;
    }
    static fromRect(other?: { x?: number; y?: number; width?: number; height?: number }) {
      return new DOMRect(other?.x ?? 0, other?.y ?? 0, other?.width ?? 0, other?.height ?? 0);
    }
    toJSON() {
      return JSON.stringify(this);
    }
  }
  (globalThis as unknown as { DOMRect: unknown }).DOMRect = DOMRect;
}

if (typeof window !== 'undefined' && typeof (window as unknown as { addEventListener?: unknown }).addEventListener !== 'function') {
  (window as unknown as { addEventListener: () => void }).addEventListener = () => {};
  (window as unknown as { removeEventListener: () => void }).removeEventListener = () => {};
}

import { registerRootComponent } from 'expo';
import App from './App';

registerRootComponent(App);
