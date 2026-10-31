// @ts-check
import {
  defineConfig,
  fontProviders,
} from "astro/config";


// https://astro.build/config
export default defineConfig({
  site: 'https://lulietlyan.github.io',
  base: '/XENIA/',
  output: 'static',
  trailingSlash: 'always',
  scopedStyleStrategy: 'where',
  fonts: [
    {
      provider: fontProviders.local(),
      name: "Roboto Slab",
      cssVariable: "--font-roboto-slab",
      options: { variants: [{ src: ["./src/assets/fonts/roboto-slab.woff2"], weight: "100 900", style: "normal" }] },
    },
    {
      provider: fontProviders.local(),
      name: "Inter",
      cssVariable: "--font-inter",
      options: { variants: [{ src: ["./src/assets/fonts/inter.woff2"], weight: "100 900", style: "normal" }] },
    },
  ],
});
