<template>
  <div class="persons-tab">
    <!-- Con personas -->
    <div v-if="hasPersons" class="pa-3">
      <div class="persons-grid">
        <v-card
          v-for="(person, idx) in persons"
          :key="idx"
          class="person-card mb-2"
          variant="outlined"
        >
          <v-card-text class="pa-3">
            <div class="d-flex align-center">
              <v-avatar
                size="40"
                :color="getRoleColor(person.role)"
                class="me-3"
              >
                <v-icon color="white">mdi-account</v-icon>
              </v-avatar>
              <div class="flex-grow-1">
                <div class="text-subtitle-2 font-weight-bold">
                  {{ person.name || person.person?.name }}
                </div>
                <v-chip
                  v-if="person.role"
                  size="x-small"
                  :color="getRoleColor(person.role)"
                  variant="flat"
                  class="mt-1"
                >
                  {{ person.role }}
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- Sin personas -->
    <div v-else class="pa-3 text-center empty-state">
      <v-icon size="48" color="grey-lighten-1">mdi-account-off</v-icon>
      <p class="text-caption text-grey mt-2">No hay personas registradas</p>
    </div>
  </div>
</template>

<script setup>
import { useColors } from "@/composables/useColors";

const { colors } = useColors();

defineProps({
  persons: {
    type: Array,
    default: () => [],
  },
  hasPersons: {
    type: Boolean,
    default: false,
  },
});

function getRoleColor(role) {
  if (!role) return colors.brownGrey;

  const roleLower = role.toLowerCase();

  // Usar colores del Poder Judicial para roles principales
  if (roleLower.includes("demandante") || roleLower.includes("actor")) {
    return colors.redPrimary; // Rojo principal PJ
  }
  if (roleLower.includes("demandado")) {
    return colors.redDark; // Rojo oscuro PJ
  }
  if (roleLower.includes("juez") || roleLower.includes("magistrado")) {
    return colors.brownGrey; // Gris/Marrón PJ
  }
  if (roleLower.includes("secretario")) {
    return "#4A5568"; // Gris oscuro
  }
  if (roleLower.includes("testigo")) {
    return colors.redLight; // Rosa claro PJ
  }
  if (roleLower.includes("perito")) {
    return "#2D3748"; // Casi negro
  }
  if (roleLower.includes("abogado")) {
    return colors.redDark; // Rojo oscuro PJ
  }

  return colors.brownGrey; // Default: Gris/Marrón PJ
}
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.persons-grid {
  max-height: 500px;
  overflow-y: auto;
  @include scrollbar-pj;
}

.person-card {
  transition: all $transition-fast;
  cursor: default;
  border-color: rgba($pj-brown-grey, 0.2);

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-pj-md;
    border-color: $pj-red-light;
  }
}

.empty-state {
  padding: $spacing-3xl $spacing-xl;
}
</style>
