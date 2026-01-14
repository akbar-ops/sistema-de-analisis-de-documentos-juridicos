// frontend/src/main.js
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";

// 🎨 Importar estilos globales del sistema de diseño
import "@/styles/variables.scss";
import "@/styles/utilities.scss";

// 🎨 Colores personalizados del Poder Judicial de Perú
const docanaLight = {
  dark: false,
  colors: {
    background: "#FFFFFF",
    surface: "#F2F2F2", // Gris muy claro PJ
    primary: "#8C0D0D", // Rojo principal PJ
    primary: "#8C0D0D", // Rojo principal PJ
    secondary: "#736D5D", // Gris/Marrón PJ
    accent: "#731414", // Rojo oscuro PJ
    error: "#8C0D0D",
    info: "#736D5D",
    success: "#736D5D",
    warning: "#D9A3A3", // Rosa claro PJ
    "on-background": "#1C0000",
    "on-surface": "#1C0000",
  },
};

const docanaDark = {
  dark: true,
  colors: {
    background: "#1C0000",
    surface: "#2B1B1B",
    primary: "#8C0D0D", // Rojo principal PJ
    secondary: "#736D5D", // Gris/Marrón PJ
    accent: "#D9A3A3", // Rosa claro PJ
    error: "#8C0D0D",
    info: "#736D5D",
    success: "#736D5D",
    warning: "#D9A3A3",
    "on-background": "#FFFFFF",
    "on-surface": "#FFFFFF",
  },
};

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "docanaLight",
    themes: {
      docanaLight,
      docanaDark,
    },
  },
});

createApp(App).use(vuetify).use(router).mount("#app");
