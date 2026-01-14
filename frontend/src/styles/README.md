# 🎨 Sistema de Diseño - Poder Judicial del Perú

Este directorio contiene el **sistema de diseño centralizado** para la aplicación de gestión de documentos judiciales.

---

## 📁 Archivos

### **variables.scss** ⭐ ESENCIAL

Sistema completo de variables y mixins:

- **Colores oficiales PJ** (#736D5D, #8C0D0D, #731414, #D9A3A3, #F2F2F2)
- **Espaciado** (xs → 3xl)
- **Tipografía** (fuentes, tamaños, pesos)
- **Sombras** (con identidad PJ)
- **Transiciones** (fast, base, slow)
- **Z-index layers** (dropdown, modal, tooltip, header)
- **Breakpoints** (sm, md, lg, xl)
- **Mixins reutilizables**:
  - `@mixin pj-card`
  - `@mixin pj-button-primary`
  - `@mixin pj-button-secondary`
  - `@mixin scrollbar-pj`
  - `@mixin truncate-text($lines)`
  - `@mixin responsive($breakpoint)`

### **utilities.scss**

Clases de utilidad reutilizables:

- Clases de color (`.text-pj-red`, `.bg-pj-grey`)
- Clases de componentes (`.pj-card`, `.pj-btn-primary`)
- Clases de estado (`.hover-pj-red`, `.hover-scale`)
- Clases de espaciado (`.gap-xs`, `.gap-sm`)

### **settings.scss**

Configuraciones globales de Vuetify (legacy, mantener por compatibilidad).

---

## 🚀 Uso Rápido

### En cualquier componente Vue:

```vue
<template>
  <v-card class="my-card">
    <v-card-title class="title">Título</v-card-title>
    <v-card-text>Contenido</v-card-text>
  </v-card>
</template>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.my-card {
  border-radius: $border-radius-md; // 8px
  padding: $spacing-md; // 16px
  box-shadow: $shadow-pj-md; // Sombra PJ

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-pj-lg;
  }
}

.title {
  color: $pj-red-primary; // #8C0D0D
  @include truncate-text(2); // Truncar a 2 líneas
}
</style>
```

---

## 🎨 Paleta de Colores PJ

```scss
$pj-brown-grey: #736d5d; // Gris/Marrón institucional
$pj-red-primary: #8c0d0d; // Rojo principal
$pj-red-dark: #731414; // Rojo oscuro
$pj-red-light: #d9a3a3; // Rosa claro
$pj-grey-light: #f2f2f2; // Gris muy claro
```

**Usar:**

- `$pj-red-primary` → Botones primarios, links, badges importantes
- `$pj-brown-grey` → Botones secundarios, texto de apoyo
- `$pj-red-dark` → Estados activos, énfasis
- `$pj-red-light` → Hover states, fondos suaves
- `$pj-grey-light` → Backgrounds, cards

---

## 📐 Espaciado Consistente

```scss
$spacing-xs:   4px    // Gaps muy pequeños
$spacing-sm:   8px    // Padding compacto, gaps
$spacing-md:   16px   // Estándar (default)
$spacing-lg:   24px   // Secciones, separadores
$spacing-xl:   32px   // Containers
$spacing-2xl:  48px   // Separaciones grandes
$spacing-3xl:  64px   // Empty states
```

---

## 🔧 Mixins Útiles

### `@mixin pj-card`

Card con estilo PJ listo para usar:

```scss
.my-card {
  @include pj-card;
}
```

### `@mixin scrollbar-pj`

Scrollbar personalizado con colores PJ:

```scss
.scrollable {
  overflow-y: auto;
  @include scrollbar-pj;
}
```

### `@mixin truncate-text($lines)`

Truncar texto a N líneas con "...":

```scss
.title {
  @include truncate-text(2); // Truncar a 2 líneas
}
```

### `@mixin responsive($breakpoint)`

Media queries estandarizadas:

```scss
.container {
  padding: $spacing-xl;

  @include responsive(md) {
    padding: $spacing-md; // En pantallas ≤960px
  }
}
```

**Breakpoints disponibles:**

- `sm` → ≤600px
- `md` → ≤960px
- `lg` → ≤1280px
- `xl` → ≤1920px

---

## ✅ Buenas Prácticas

### ✅ BIEN:

```scss
.card {
  padding: $spacing-md; // Variable
  color: $pj-red-primary; // Variable PJ
  box-shadow: $shadow-pj-md; // Variable PJ
  transition: all $transition-base;
}
```

### ❌ MAL:

```scss
.card {
  padding: 16px; // ❌ Hardcoded
  color: #8c0d0d; // ❌ Hardcoded
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); // ❌ Custom
  transition: all 0.25s ease; // ❌ Hardcoded
}
```

---

## 📚 Documentación Completa

Para más detalles, ejemplos y guías de migración, consulta:

1. **`/GUIA_SISTEMA_DISENO_PJ.md`** ⭐ Guía rápida de uso
2. **`/EJEMPLOS_MIGRACION_SISTEMA_PJ.md`** 🔄 Ejemplos de migración
3. **`/REFACTORIZACION_COMPLETADA.md`** 📊 Resumen ejecutivo
4. **`/INDICE_DOCUMENTACION.md`** 📚 Índice completo

---

## 🎯 Ejemplos Reales

Ver componentes refactorizados como ejemplos:

- `/components/DocDetailsTabs/SimilarTab.vue` - Uso completo de variables y composables
- `/components/DocDetailsTabs/PersonsTab.vue` - Colores dinámicos PJ
- `/components/DocDetailsPanel.vue` - Estructura responsive con mixins

---

**🎨 Desarrollado siguiendo las mejores prácticas de SCSS y Vue 3**
**🏛️ Con la identidad visual oficial del Poder Judicial del Perú**
