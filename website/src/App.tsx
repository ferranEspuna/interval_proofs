import React, { useState } from 'react';
import 'katex/dist/katex.min.css';
import CandelaVisualizer from './CandelaVisualizer';
import IntervalVisualizer from './IntervalVisualizer';
import LinearFormVisualizer from './LinearFormVisualizer';
import PreimageConstructionVisualizer from './PreimageConstructionVisualizer';
import { buildShareUrl, copyText, readSharedStateFromUrl } from './shared';
import type { VisualizerMode } from './ui';

function readInitialVisualizerMode(shared: any): VisualizerMode {
  if (!shared || typeof shared !== 'object') return 'candela';
  if (shared.mode === 'candela') return 'candela';
  if (shared.mode === 'linear-form') return 'linear-form';
  if (shared.mode === 'preimage-construction') return 'preimage-construction';
  if (shared.mode === 'interval') return 'interval';
  if (Array.isArray(shared.intervals)) return 'interval';
  return 'candela';
}

export default function App() {
  const [initialShared] = useState(() => readSharedStateFromUrl());
  const [mode, setMode] = useState<VisualizerMode>(() => readInitialVisualizerMode(initialShared));
  const [linearState, setLinearState] = useState<unknown>(initialShared);
  const [constructionState, setConstructionState] = useState<unknown>(initialShared);

  const showLinearForm = (setup?: unknown) => {
    setLinearState(setup);
    setMode('linear-form');
  };

  const showConstruction = (setup?: unknown) => {
    setConstructionState(setup);
    setMode('preimage-construction');
  };

  if (mode === 'preimage-construction') {
    return (
      <PreimageConstructionVisualizer
        initialState={constructionState}
        buildShareUrl={buildShareUrl}
        copyText={copyText}
        onSwitchToLinearForm={showLinearForm}
        onSwitchToIntervals={() => setMode('interval')}
        onSwitchToCandela={() => setMode('candela')}
      />
    );
  }

  if (mode === 'linear-form') {
    return (
      <LinearFormVisualizer
        initialState={linearState}
        buildShareUrl={buildShareUrl}
        copyText={copyText}
        onSwitchToIntervals={() => setMode('interval')}
        onSwitchToConstruction={showConstruction}
        onSwitchToCandela={() => setMode('candela')}
      />
    );
  }

  if (mode === 'interval') {
    return (
      <IntervalVisualizer
        onSwitchToCandela={() => setMode('candela')}
        onSwitchToLinearForm={showLinearForm}
        onSwitchToConstruction={showConstruction}
      />
    );
  }

  return (
    <CandelaVisualizer
      onSwitchToIntervals={() => setMode('interval')}
      onSwitchToLinearForm={showLinearForm}
      onSwitchToConstruction={() => showConstruction()}
    />
  );
}
