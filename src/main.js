import {createApp} from "vue";
import App from "./App.vue";
import "./styles.css";

const app = createApp(App);

app.config.devtools = true;
app.mount("#app");
