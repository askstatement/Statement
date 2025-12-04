"use client";
import * as d3 from "d3";
import { useState, useRef, useEffect } from "react";

// css
import "@/style/uiElements/barchart.scss";

// utils
import { shortenMonths } from "@/utils/dateUtils";

export default function BarChart({
  data = [30, 40, 60, 20, 40, 100, 70],
  xLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
  graphWidth = 700,
  graphHeight = 350,
  margin = { top: 0, right: 0, bottom: 0, left: 0 },
  title = "",
  currValue = "",
  percentage = "",
  amount = "",
  currency = "",
}) {
  xLabels = shortenMonths(xLabels);
  // currValue = data[data.length - 1].toFixed();

  // validate data
  data = data.map((d) => (d ? d : 0));

  const [hoveredBar, setHoveredBar] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  const innerWidth = dimensions.width - margin.left - margin.right;
  const innerHeight = dimensions.height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(d3.range(data.length + 1))
    .range([0, innerWidth])
    .padding(0.2);

  const yMax = d3.max(data);
  const yPadding = yMax * 0.1;

  // Fix: always start y-scale from 0
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax + yPadding])
    .nice()
    .range([innerHeight, 40]);

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({
        width: graphWidth || width,
        height: graphHeight || height,
      });
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  const handleMouseMove = (e, i) => {
    if (!svgRef.current || !containerRef.current) return;

    const svgRect = svgRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();

    const svgX = xScale(i) + xScale.bandwidth() / 2;
    const svgY = yScale(data[i]);

    const left = svgRect.left - containerRect.left + margin.left + svgX;
    const top = svgRect.top - containerRect.top + margin.top + svgY;

    setHoveredBar({
      index: i,
      value: data[i],
      svgX,
      svgY,
      left,
      top,
      label: xLabels[i],
    });
  };

  const handleMouseLeave = () => setHoveredBar(null);

  const switchData = (e) => {
    const target = e.target;
    target.parentNode
      .querySelectorAll("span")
      .forEach((span) => span.classList.remove("_active"));
    target.classList.add("_active");
  };

  function shortenText(input, maxLength) {
    if (!input) return "";
    const words = input.split(" ");
    if (words.length <= 3) return input;
    return input.length > maxLength
      ? input.slice(0, maxLength - 3) + "..."
      : input;
  }

  return (
    <div
      className="d3_container barchart"
      ref={containerRef}
      style={{ position: "relative" }}
    >
      <svg
        width={dimensions.width}
        height={dimensions.height}
        ref={svgRef}
        style={{
          display: "block",
          margin: "0 auto",
          background: "rgb(31,31,31)",
          borderRadius: 8,
        }}
      >
        <g transform={`translate(${margin.left},${margin.top})`}>
          {/* defs for gradient */}
          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00CB7D" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#00CB7D" stopOpacity={0.2} />
            </linearGradient>
          </defs>

          {/* grids */}
          {yScale.ticks(5).map((tick) => (
            <line
              key={tick}
              x1={0}
              x2={innerWidth}
              y1={yScale(tick)}
              y2={yScale(tick)}
              stroke="rgba(255,255,255,0.08)"
            />
          ))}

          {/* bars */}
          {data.map((d, i) => {
            const barHeight = Math.max(0, innerHeight - yScale(d));
            return (
              <rect
                key={i}
                x={xScale(i) + xScale.bandwidth() * 0.3}
                y={yScale(d)}
                width={xScale.bandwidth() * 0.4}
                height={barHeight}
                fill="url(#barGradient)"
                onMouseMove={(e) => handleMouseMove(e, i)}
                onMouseLeave={handleMouseLeave}
              />
            );
          })}

          {/* X axis labels */}
          <g className="d3_xaxis" transform={`translate(0,${innerHeight})`}>
            {xLabels.map((label, i) => (
              <g
                key={label}
                transform={`translate(${xScale(i) + xScale.bandwidth() / 2},0)`}
              >
                <text dy="-5%" textAnchor="middle" fill="#81827e" opacity={0.6}>
                  {label}
                </text>
              </g>
            ))}
          </g>

          {/* Y axis labels */}
          <g className="d3_yaxis">
            {yScale.ticks(5).map((tick) => (
              <g key={tick} transform={`translate(0,${yScale(tick)})`}>
                <text
                  dx="5%"
                  dy="-10"
                  textAnchor="end"
                  fill="#81827e"
                  opacity={0.6}
                >
                  {currency ? `${currency}` : ""}{tick}
                </text>
              </g>
            ))}
          </g>

          {/* hover line */}
          {hoveredBar && (
            <line
              x1={hoveredBar.svgX}
              x2={hoveredBar.svgX}
              y1={0}
              y2={innerHeight}
              stroke="#a6a6a657"
              strokeWidth={1}
              pointerEvents="none"
            />
          )}
        </g>
      </svg>

      {title && (
        <div className="d3_data_details">
          <div className="_wrap">
            <img className="_logo" src="/next_images/statement_logo.svg" />
            <div className="data_display">
              <h2>
                {shortenText(title, 30)}
                {currValue ? ` $${currValue}` : ""}
              </h2>
              {percentage && (
                <p>
                  {amount && <span>{`$ ${amount}`}</span>}
                  <span>
                    <img src="/next_images/increment.svg" />
                    {percentage}
                  </span>
                </p>
              )}
            </div>
          </div>
          <div className="d3_data_switch">
            <span onClick={switchData}>1D</span>
            <span onClick={switchData}>1W</span>
            <span onClick={switchData}>1M</span>
            <span onClick={switchData}>3M</span>
            <span onClick={switchData}>1Y</span>
          </div>
        </div>
      )}

      {/* Tooltip */}
      {hoveredBar && (
        <div
          className="tooltip"
          style={{
            position: "absolute",
            left: `calc(${hoveredBar.left}px - 70px)`,
            top: `${hoveredBar.top - 20}px`,
            transform: "translateY(-50%)",
            pointerEvents: "none",
            whiteSpace: "nowrap",
            height: "fit-content",
          }}
        >
          <p>
            {hoveredBar.label}: {hoveredBar.value.toFixed(2)}
          </p>
        </div>
      )}
    </div>
  );
}
