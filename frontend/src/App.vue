<template>
  <v-app>
    <!-- Barra superior -->
    <HeaderBar />

    <!-- Contenido principal -->
    <v-main class="main-content">
      <div class="app-layout">
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <div :key="route.path" class="view-container">
              <component :is="Component" />
            </div>
          </transition>
        </router-view>

        <!-- Footer -->
        <FooterBar />
      </div>
    </v-main>
  </v-app>
</template>

<script setup>
import { onMounted } from "vue";
import { useTheme } from "vuetify";
import HeaderBar from "./components/HeaderBar.vue";
import FooterBar from "./components/FooterBar.vue";

/* ------------------ Tema ------------------ */
const theme = useTheme();

/* ------------------ Ciclo de vida ------------------ */
onMounted(() => {
  // Usar siempre el tema claro
  theme.global.name.value = "docanaLight";
});
</script>

<style>
/* ===== �� Base ===== */
html,
body,
#app,
.v-application {
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

* {
  box-sizing: border-box;
}

/* ===== 🌐 Main Content ===== */
.main-content {
  padding-top: 96px !important; /* Altura del header */
  height: 100vh;
  overflow: hidden;
  background-color: rgb(var(--v-theme-background)) !important;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

.view-container {
  flex: 1 0 auto;
  width: 100%;
}

/* ===== 🎭 Transiciones ===== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ===== 📦 Cards ===== */
.v-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 🎯 Scrollbar personalizado ===== */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* Dark mode scrollbar */
.v-theme--dark ::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.v-theme--dark ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
}

.v-theme--dark ::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* ===== Tipografía ===== */
.v-application {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
}
</style>
