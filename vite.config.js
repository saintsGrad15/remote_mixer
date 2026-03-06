import {defineConfig} from "vite";
import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";
import path from "path";

export default defineConfig({
    plugins: [vue(), vueDevTools()],
    root: ".",
    base: "/static/dist/",
    build: {
        sourcemap: true,
        minify: false,
        outDir: "static/dist",
        emptyOutDir: true,
        rollupOptions: {
            input: path.resolve(__dirname, "index.html")
        }
    },
    server: {
        proxy: {
            "/config": "http://localhost:5001",
            "/ws": {
                target: "ws://localhost:5001",
                ws: true
            }
        }
    }
});

