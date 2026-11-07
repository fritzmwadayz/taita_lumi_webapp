<template>
  <div class="flex flex-wrap items-center gap-2">
    <span class="text-xs text-stone-light mr-1">Share:</span>
    <a
      :href="xUrl"
      target="_blank"
      rel="noopener"
      class="focus-ring flex items-center gap-1.5 text-xs font-medium text-ink-soft border border-cream-300 rounded-lg px-2.5 py-1.5 hover:bg-cream-100 transition"
      title="Share on X"
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <path
          d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
        />
      </svg>
      X
    </a>
    <a
      :href="whatsappUrl"
      target="_blank"
      rel="noopener"
      class="focus-ring flex items-center gap-1.5 text-xs font-medium text-ink-soft border border-cream-300 rounded-lg px-2.5 py-1.5 hover:bg-cream-100 transition"
      title="Share on WhatsApp"
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <path
          d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"
        />
      </svg>
      WhatsApp
    </a>
    <button
      class="focus-ring flex items-center gap-1.5 text-xs font-medium text-ink-soft border border-cream-300 rounded-lg px-2.5 py-1.5 hover:bg-cream-100 transition"
      title="Copy link"
      @click="copyLink"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
        />
      </svg>
      <span v-if="!copied">Copy</span>
      <span v-else class="text-forest">Copied!</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  headword: string
  wordSlug: string
}>()

const copied = ref(false)

// SSR-safe: useRequestURL() works on both server and client
const route = useRoute()
const shareUrl = computed(() => {
  // On client, use window.location.origin; on server, reconstruct from request
  if (import.meta.client) {
    return `${window.location.origin}/words/${props.wordSlug}`
  }
  // During SSR, use the request URL origin
  const reqUrl = useRequestURL()
  return `${reqUrl.origin}/words/${props.wordSlug}`
})

const shareText = computed(() => `${props.headword} — Lumi dictionary`)

const xUrl = computed(
  () =>
    `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText.value)}&url=${encodeURIComponent(shareUrl.value)}`,
)

const whatsappUrl = computed(
  () =>
    `https://wa.me/?text=${encodeURIComponent(shareText.value + ' ' + shareUrl.value)}`,
)

async function copyLink() {
  if (!import.meta.client) return
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>
