<template>
  <span v-if="pos" :class="badgeClass" class="pos-badge">
    {{ pos }}
  </span>
  <span v-else class="text-[10px] text-stone-light italic">no POS yet</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  pos: { type: String, default: null },
});

const badgeClass = computed(() => {
  switch (props.pos) {
    case "noun":
      return "pos-noun";
    case "verb":
      return "pos-verb";
    case "adjective":
    case "adj":
      return "pos-adj";
    case "phrase":
      return "pos-phrase";
    default:
      return "pos-noun";
  }
});
</script>

<style scoped>
.pos-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.pos-noun {
  background: #e8dfc8;
  color: #2d5a3d;
}
.pos-verb {
  background: #f5efe3;
  color: #c75b39;
}
.pos-adj {
  background: #faf0e0;
  color: #a8492b;
}
.pos-phrase {
  background: #ede4d1;
  color: #6b7280;
}
</style>
