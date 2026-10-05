<template>
  <!-- L'app installée sur iPhone/iPad passe sous la barre d'état (`black-translucent`), dont le texte est toujours
       blanc : sur un fond clair, ce bandeau sombre derrière lui le garde lisible. Hauteur nulle partout où le système
       ne réserve pas de zone en haut (navigateur, Android, ordinateur). -->
  <div
    class="pointer-events-none fixed inset-x-0 top-0 z-[130] h-[env(safe-area-inset-top)] bg-[#1b1813]"
    aria-hidden="true"
  ></div>
</template>
