import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';
import { IncidentData } from '../types';

interface TimelineSliderProps {
  data?: IncidentData | null;
  timelineMinutes: number;
  onChangeTimeline: (minutes: number) => void;
}

export const TimelineSlider: React.FC<TimelineSliderProps> = ({
  data,
  timelineMinutes,
  onChangeTimeline
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const totalMinutes = 720; // Generic 12 hours


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
    const baseDate = new Date("2019-06-10T12:00:00Z");
    const targetDate = new Date(baseDate.getTime() + minutes * 60 * 1000);
    const hour = targetDate.getUTCHours().toString().padStart(2, '0');
    const min = targetDate.getUTCMinutes().toString().padStart(2, '0');
    return `${hour}:${min} UTC (10 JUN 2019)`;
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
          {data?.origin_estimate && (
            <div
              className="absolute h-3 bg-blue-600/30 border-x border-blue-500 pointer-events-none"
              style={{ left: `20%`, width: `10%` }}
            />
          )}

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
      {data?.scene && (
        <div className="flex items-center gap-3 text-[10px] text-zinc-500 shrink-0">
          <span className="flex items-center gap-1 text-blue-400">
            <span className="w-2 h-2 bg-blue-500" />
            ORIGIN WINDOW
          </span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="w-2 h-2 bg-white" />
            SAR PASS ({data.scene.acquisition_time.split('T')[1].substring(0, 5)} UTC)
          </span>
        </div>
      )}
    </div>
  );
};
