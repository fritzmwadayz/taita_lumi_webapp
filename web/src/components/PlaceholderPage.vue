<template>
  <div class="px-12 py-20 max-w-3xl mx-auto">
    <p
      class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3"
    >
      {{ phase }}
    </p>
    <h1 class="font-serif text-4xl text-forest-dark mb-4">
      {{ title }}
    </h1>
    <p class="text-base text-stone leading-relaxed mb-8">
      {{ description }}
    </p>
    <div
      class="bg-cream-100 border border-cream-200 rounded-xl p-5 text-sm text-stone"
    >
      <p class="font-medium text-ink mb-2">This is a placeholder.</p>
      <p>
        The route exists so the app doesn't 404, but the real implementation
        comes in <strong>{{ phase }}</strong>. See
        <code class="font-mono text-xs bg-cream-200 px-1.5 py-0.5 rounded"
          >download/TaitaLumi_UI_Mockup_v0.2.html</code
        >
        for the intended design.
      </p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  phase: { type: String, required: true },
  description: { type: String, required: true },
});
</script>
