<template>
  <div class="loading-state" :class="sizeClass">
    <v-progress-circular :indeterminate="true" :size="size" :color="color" />
    <p v-if="message" class="loading-message mt-3" :class="messageClass">
      {{ message }}
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  size: {
    type: [String, Number],
    default: 32,
  },
  color: {
    type: String,
    default: "#8C0D0D", // PJ red primary
  },
  message: {
    type: String,
    default: "",
  },
  variant: {
    type: String,
    default: "default", // 'default' | 'compact' | 'large'
    validator: (value) => ["default", "compact", "large"].includes(value),
  },
});

const sizeClass = computed(() => `loading-state--${props.variant}`);
const messageClass = computed(() => `text-${props.variant}`);
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  &--compact {
    padding: $spacing-sm;
  }

  &--default {
    padding: $spacing-lg;
  }

  &--large {
    padding: $spacing-3xl $spacing-xl;
  }
}

.loading-message {
  color: rgba(0, 0, 0, 0.6);
  font-size: $font-size-sm;

  &.text-compact {
    font-size: $font-size-xs;
  }

  &.text-large {
    font-size: $font-size-md;
  }
}
</style>
