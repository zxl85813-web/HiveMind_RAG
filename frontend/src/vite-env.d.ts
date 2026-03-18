/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

// CSS Modules 类型声明
declare module '*.module.css' {
    const classes: { readonly [key: string]: string };
    export default classes;
}
