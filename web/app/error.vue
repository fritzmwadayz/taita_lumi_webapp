<template>
  <div class="min-h-screen flex flex-col bg-cream">
    <AppNavbar />
    <main class="flex-1 flex items-center justify-center px-12 py-24">
      <div class="text-center max-w-md">
        <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">
          {{ error.statusCode === 404 ? '404' : 'Error' }}
        </p>
        <h1 class="font-serif text-4xl md:text-5xl text-forest-dark mb-4">
          {{ error.statusCode === 404 ? "This page doesn't exist." : 'Something went wrong.' }}
        </h1>
        <p class="text-base text-stone mb-8">
          {{
            error.statusCode === 404
              ? 'Maybe the URL is wrong, or this page hasn\'t been built yet.'
              : error.message || 'An unexpected error occurred.'
          }}
        </p>
        <NuxtLink
          to="/"
          class="focus-ring btn btn-primary btn-md"
        >
          Back to home
        </NuxtLink>
      </div>
    </main>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import type { NuxtError } from '#app'

defineProps<{ error: NuxtError }>()
</script>
