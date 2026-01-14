<template>
  <header class="header">
    <div class="header__container">
      <!-- Logo y Branding -->
      <router-link to="/" class="header__brand">
        <div class="header__logo" aria-label="Logo Poder Judicial">
          <img
            src="@/assets/logo-pj.png"
            alt="Logo Poder Judicial"
            class="header__logo-img"
          />
        </div>
      </router-link>

      <!-- Navegación Desktop -->
      <nav
        class="header__nav d-none d-md-flex"
        role="navigation"
        aria-label="Navegación principal"
      >
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="header__nav-link"
          :class="{ 'header__nav-link--active': isActive(item.path) }"
        >
          <v-icon size="30" class="header__nav-icon">{{ item.icon }}</v-icon>
          <span class="header__nav-text">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- Botón menú móvil -->
      <button
        class="header__mobile-toggle d-md-none"
        @click="drawer = !drawer"
        aria-label="Abrir menú"
        :aria-expanded="drawer"
      >
        <v-icon size="42" color="white">{{
          drawer ? "mdi-close" : "mdi-menu"
        }}</v-icon>
      </button>
    </div>
  </header>

  <!-- Drawer para móvil -->
  <v-navigation-drawer
    v-model="drawer"
    location="right"
    temporary
    width="300"
    class="header__drawer d-md-none"
  >
    <div class="header__drawer-header">
      <img
        src="@/assets/logo-pj.png"
        alt="Logo Poder Judicial"
        class="header__drawer-logo"
      />
    </div>

    <v-divider />

    <v-list nav density="comfortable" class="header__drawer-nav">
      <v-list-item
        v-for="item in navItems"
        :key="item.path"
        :value="item.path"
        :active="isActive(item.path)"
        @click="navigateTo(item.path)"
        rounded="lg"
        class="header__drawer-item"
      >
        <template #prepend>
          <v-icon :color="isActive(item.path) ? 'primary' : undefined">
            {{ item.icon }}
          </v-icon>
        </template>
        <v-list-item-title class="header__drawer-item-text">
          {{ item.label }}
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup>
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";

const router = useRouter();
const route = useRoute();
const drawer = ref(false);

// Configuración de navegación centralizada
const navItems = [
  { path: "/", label: "Inicio", icon: "mdi-home-outline" },
  { path: "/simple", label: "Análisis", icon: "mdi-file-document-outline" },
  { path: "/queue", label: "Cola de Tareas", icon: "mdi-format-list-checks" },
  { path: "/clusters", label: "Clusters", icon: "mdi-chart-bubble" },
  { path: "/topics", label: "Tópicos", icon: "mdi-tag-multiple" },
  { path: "/stats", label: "Estadísticas", icon: "mdi-chart-line-variant" },
];

function isActive(path) {
  if (path === "/") {
    return route.path === "/";
  }
  return route.path.startsWith(path);
}

function navigateTo(path) {
  router.push(path);
  drawer.value = false;
}
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

// ============================================================================
// HEADER PROFESIONAL - FONDO ROJO INSTITUCIONAL
// ============================================================================

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: $z-header;
  background: linear-gradient(135deg, $pj-red-primary 0%, $pj-red-dark 100%);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.header__container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-sm $spacing-xl;
  gap: $spacing-lg;

  @media (max-width: $breakpoint-sm) {
    padding: $spacing-sm $spacing-md;
  }
}

// Brand / Logo
.header__brand {
  display: flex;
  align-items: center;
  text-decoration: none;
  transition: opacity $transition-fast;
  flex-shrink: 0;

  &:hover {
    opacity: 0.9;
  }
}

.header__logo {
  height: 72px;
  display: flex;
  align-items: center;

  @media (max-width: $breakpoint-sm) {
    height: 60px;
  }
}

.header__logo-img {
  height: 100%;
  width: auto;
  object-fit: contain;
  filter: brightness(1.05);
}

// Navegación Desktop
.header__nav {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.header__nav-link {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $border-radius-md;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.9);
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  transition: all $transition-fast;
  position: relative;

  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: white;
  }

  &--active {
    background: rgba(255, 255, 255, 0.2);
    color: white;

    &::after {
      content: "";
      position: absolute;
      bottom: 0;
      left: $spacing-md;
      right: $spacing-md;
      height: 3px;
      background: white;
      border-radius: 3px 3px 0 0;
    }
  }
}

.header__nav-icon {
  opacity: 0.9;
  color: inherit;
}

.header__nav-text {
  white-space: nowrap;
}

// Mobile Toggle
.header__mobile-toggle {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: $spacing-sm;
  cursor: pointer;
  color: white;
  border-radius: $border-radius-md;
  transition: all $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  &:focus-visible {
    outline: 2px solid white;
    outline-offset: 2px;
  }
}

// Drawer Móvil
.header__drawer {
  background: rgb(var(--v-theme-surface)) !important;
}

.header__drawer-header {
  padding: $spacing-lg;
  background: linear-gradient(135deg, $pj-red-primary 0%, $pj-red-dark 100%);
  display: flex;
  justify-content: center;
  align-items: center;
}

.header__drawer-logo {
  height: 66px;
  width: auto;
  object-fit: contain;
}

.header__drawer-nav {
  padding: $spacing-md;
}

.header__drawer-item {
  margin-bottom: $spacing-xs;

  &:deep(.v-list-item__prepend) {
    margin-right: $spacing-md;
  }
}

.header__drawer-item-text {
  font-weight: $font-weight-medium;
}
</style>
