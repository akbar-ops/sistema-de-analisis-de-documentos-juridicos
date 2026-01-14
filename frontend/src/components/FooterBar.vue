<template>
  <footer class="footer">
    <div class="footer__container">
      <!-- Contenido principal del footer -->
      <div class="footer__content">
        <!-- Columna de información institucional -->
        <div class="footer__section footer__section--brand">
          <div class="footer__brand">
            <div class="header__logo" aria-label="Logo Poder Judicial">
              <img
                src="@/assets/logo-pj.png"
                alt="Logo Poder Judicial"
                class="header__logo-img"
              />
            </div>
          </div>
          <p class="footer__description">
            Sistema de Gestión Documental para el análisis y organización
            inteligente de documentos judiciales.
          </p>
        </div>

        <!-- Columna de enlaces rápidos -->
        <div class="footer__section">
          <h4 class="footer__section-title">Enlaces Rápidos</h4>
          <nav class="footer__nav" aria-label="Enlaces del footer">
            <router-link to="/" class="footer__link">
              <v-icon size="16" class="mr-1">mdi-home-outline</v-icon>
              Inicio
            </router-link>
            <router-link to="/simple" class="footer__link">
              <v-icon size="16" class="mr-1">mdi-file-document-outline</v-icon>
              Análisis de Documentos
            </router-link>
            <router-link to="/queue" class="footer__link">
              <v-icon size="16" class="mr-1">mdi-format-list-checks</v-icon>
              Cola de Tareas
            </router-link>
            <router-link to="/clusters" class="footer__link">
              <v-icon size="16" class="mr-1">mdi-chart-bubble</v-icon>
              Visualización de Clusters
            </router-link>
            <router-link to="/stats" class="footer__link">
              <v-icon size="16" class="mr-1">mdi-chart-line-variant</v-icon>
              Estadísticas
            </router-link>
          </nav>
        </div>

        <!-- Columna de contacto -->
        <div class="footer__section">
          <h4 class="footer__section-title">Información</h4>
          <ul class="footer__info-list">
            <li class="footer__info-item">
              <v-icon size="16" class="footer__info-icon"
                >mdi-clock-outline</v-icon
              >
              <span>Lunes a Viernes: 8:00 - 17:00</span>
            </li>
            <li class="footer__info-item">
              <v-icon size="16" class="footer__info-icon"
                >mdi-email-outline</v-icon
              >
              <span>soporte@pj.gob.pe</span>
            </li>
            <li class="footer__info-item">
              <v-icon size="16" class="footer__info-icon"
                >mdi-phone-outline</v-icon
              >
              <!-- <span>(01) 410-1010</span> -->
              <span>(01) 000-0000</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Divider -->
      <div class="footer__divider"></div>

      <!-- Bottom bar -->
      <div class="footer__bottom">
        <p class="footer__copyright">
          © {{ currentYear }} Poder Judicial del Perú. Todos los derechos
          reservados.
        </p>
        <div class="footer__legal">
          <a href="#" class="footer__legal-link">Política de Privacidad</a>
          <span class="footer__legal-separator">|</span>
          <a href="#" class="footer__legal-link">Términos de Uso</a>
          <span class="footer__legal-separator">|</span>
          <a href="#" class="footer__legal-link">Accesibilidad</a>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from "vue";

const currentYear = computed(() => new Date().getFullYear());
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

// ============================================================================
// FOOTER PROFESIONAL
// ============================================================================

.footer {
  background: linear-gradient(
    180deg,
    $pj-red-dark 0%,
    darken($pj-red-dark, 5%) 100%
  );
  color: white;
  padding: $spacing-2xl $spacing-lg $spacing-lg;
  margin-top: auto;
  flex-shrink: 0;

  @media (max-width: $breakpoint-sm) {
    padding: $spacing-xl $spacing-md $spacing-md;
  }
}

.footer__container {
  padding: 0;
}

// Contenido principal
.footer__content {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: $spacing-2xl;

  @media (max-width: $breakpoint-md) {
    grid-template-columns: 1fr 1fr;
  }

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: 1fr;
    gap: $spacing-xl;
  }
}

// Secciones
.footer__section {
  &--brand {
    @media (max-width: $breakpoint-md) {
      grid-column: 1 / -1;
    }
  }
}

.footer__section-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 $spacing-md;
  color: rgba(255, 255, 255, 0.9);
  position: relative;
  padding-bottom: $spacing-sm;

  &::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    width: 40px;
    height: 2px;
    background: $pj-red-light;
    border-radius: 2px;
  }
}

// Brand
.footer__brand {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  margin-bottom: $spacing-md;
}

.footer__logo {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: $border-radius-md;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.footer__logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.footer__brand-text {
  display: flex;
  flex-direction: column;
}

.footer__title {
  font-size: $font-size-xl;
  font-weight: $font-weight-bold;
  margin: 0;
  line-height: 1.2;
}

.footer__subtitle {
  font-size: $font-size-sm;
  margin: 2px 0 0;
  opacity: 0.85;
}

.footer__description {
  font-size: $font-size-sm;
  line-height: 1.6;
  opacity: 0.85;
  margin: 0;
  max-width: 400px;
}

// Navegación
.footer__nav {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.footer__link {
  display: inline-flex;
  align-items: center;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: $font-size-sm;
  padding: $spacing-xs 0;
  transition: all $transition-fast;
  width: fit-content;

  &:hover {
    color: white;
    padding-left: $spacing-xs;
  }
}

// Lista de información
.footer__info-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.footer__info-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-sm;
  color: rgba(255, 255, 255, 0.85);
}

.footer__info-icon {
  opacity: 0.7;
}

// Divider
.footer__divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.15);
  margin: $spacing-xl 0 $spacing-lg;
}

// Bottom bar
.footer__bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-md;

  @media (max-width: $breakpoint-sm) {
    flex-direction: column;
    text-align: center;
  }
}

.footer__copyright {
  font-size: $font-size-xs;
  margin: 0;
  opacity: 0.75;
}

.footer__legal {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;
  justify-content: center;
}

.footer__legal-link {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  font-size: $font-size-xs;
  transition: color $transition-fast;

  &:hover {
    color: white;
    text-decoration: underline;
  }
}

.footer__legal-separator {
  color: rgba(255, 255, 255, 0.4);
  font-size: $font-size-xs;
}
</style>
