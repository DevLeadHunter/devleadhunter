<template>
  <div class="phone">
    <div class="phone__screen" :class="{ 'phone__screen--lock': props.screen === 'lock' }">
      <div class="phone__island" aria-hidden="true" />
      <div class="phone__statusbar" :class="{ 'phone__statusbar--light': props.screen === 'lock' }" aria-hidden="true">
        <span>{{ props.time }}</span>
        <span class="phone__statusbar-right">
          <span class="phone__signal"><i /><i /><i /><i /></span>
          <span class="phone__battery" />
        </span>
      </div>
      <div class="phone__body">
        <slot />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { AssistantDemoPhoneFrameProps, AssistantDemoPhoneScreen } from '~/types/AssistantDemoPhoneFrame'

const props: AssistantDemoPhoneFrameProps = defineProps({
  time: {
    type: String,
    required: true,
  },
  screen: {
    type: String as PropType<AssistantDemoPhoneScreen>,
    default: 'app',
  },
})
</script>

<style scoped>
.phone {
  width: min(100%, 350px);
  border-radius: 48px;
  background: var(--ia-device);
  padding: 11px;
  box-shadow:
    0 0 0 1px var(--ia-device-edge),
    0 34px 70px -30px rgba(23, 19, 13, 0.55);
}
.phone__screen {
  position: relative;
  height: 660px;
  border-radius: 38px;
  overflow: hidden;
  background: #fbf9f3;
  display: flex;
  flex-direction: column;
}
.phone__screen--lock {
  background:
    radial-gradient(120% 80% at 20% 0%, rgba(120, 160, 190, 0.55), transparent 60%),
    radial-gradient(90% 70% at 90% 100%, rgba(180, 120, 90, 0.35), transparent 60%),
    linear-gradient(180deg, #1c2a36 0%, #0f151c 100%);
  color: #fff;
}
.phone__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.phone__body :deep(.ai-widget--inline) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.phone__body :deep(.ai-panel--inline) {
  flex: 1;
  min-height: 0;
  height: auto;
}
.phone__island {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  width: 96px;
  height: 28px;
  border-radius: 999px;
  background: #000;
  z-index: 5;
}
.phone__statusbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 26px 6px;
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.phone__statusbar--light {
  color: #fff;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 4;
}
.phone__statusbar-right {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.phone__signal {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 11px;
}
.phone__signal i {
  width: 3px;
  background: currentColor;
  border-radius: 1px;
}
.phone__signal i:nth-child(1) {
  height: 4px;
}
.phone__signal i:nth-child(2) {
  height: 6px;
}
.phone__signal i:nth-child(3) {
  height: 8px;
}
.phone__signal i:nth-child(4) {
  height: 11px;
}
.phone__battery {
  width: 24px;
  height: 11px;
  border: 1.5px solid currentColor;
  border-radius: 4px;
  position: relative;
}
.phone__battery::after {
  content: '';
  position: absolute;
  inset: 2px;
  right: 6px;
  background: currentColor;
  border-radius: 1px;
}
@media (max-width: 640px) {
  .phone {
    border-radius: 40px;
    padding: 9px;
  }
  .phone__screen {
    border-radius: 32px;
    height: 620px;
  }
}
</style>
