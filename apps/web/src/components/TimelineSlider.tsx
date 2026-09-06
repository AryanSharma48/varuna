import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';

interface TimelineSliderProps {
  timelineMinutes: number;
  onChangeTimeline: (minutes: number) => void;
}

export const TimelineSlider: React.FC<TimelineSliderProps> = ({
  timelineMinutes,
  onChangeTimeline
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const totalMinutes = 720; // 10:00 to 22:00 UTC

  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        onChangeTimeline(timelineMinutes + 4 >= totalMinutes ? 0 : timelineMinutes + 4);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isPlaying, timelineMinutes]);

  const formatTime = (minutes: number) => {
    const startHour = 10;
    const currentTotalMinutes = startHour * 60 + minutes;
    const hour = Math.floor(currentTotalMinutes / 60) % 24;
    const min = Math.floor(currentTotalMinutes % 60);
    return `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')} UTC`;
  };

  return (
    <div className="h-14 bg-black border border-zinc-800 px-4 flex items-center justify-between gap-4 shrink-0 font-mono text-xs">
      {/* Play / Pause / Reset */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="w-8 h-8 bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center font-bold"
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
        </button>

        <button
          onClick={() => {
            setIsPlaying(false);
            onChangeTimeline(0);
          }}
          className="w-8 h-8 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center"
          title="Reset"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Time label and Scrubber */}
      <div className="flex-1 flex items-center gap-4">
        <div className="text-white font-bold w-24 shrink-0">
          {formatTime(timelineMinutes)}
        </div>

        <div className="relative flex-1 flex items-center">
          {/* Origin critical window mark */}
          <div
            className="absolute h-3 bg-blue-600/30 border-x border-blue-500 pointer-events-none"
            style={{ left: `${(210 / 720) * 100}%`, width: `${(75 / 720) * 100}%` }}
          />

          <input
            type="range"
            min={0}
            max={totalMinutes}
            value={timelineMinutes}
            onChange={(e) => onChangeTimeline(Number(e.target.value))}
            className="w-full h-1 bg-zinc-800 appearance-none cursor-pointer accent-blue-600"
          />
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 text-[10px] text-zinc-500 shrink-0">
        <span className="flex items-center gap-1 text-blue-400">
          <span className="w-2 h-2 bg-blue-500" />
          ORIGIN WINDOW (13:30–14:45)
        </span>
        <span className="flex items-center gap-1 text-zinc-400">
          <span className="w-2 h-2 bg-white" />
          SAR PASS (15:10)
        </span>
      </div>
    </div>
  );
};
