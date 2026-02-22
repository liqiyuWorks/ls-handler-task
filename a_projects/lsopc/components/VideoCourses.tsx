import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Video, User } from 'lucide-react';

export interface VideoCourseItem {
  id: string;
  title: string;
  description: string;
  /** 仅支持微信扫码观看时的视频页链接，用于生成二维码 */
  watchUrl: string;
}

const COURSES: VideoCourseItem[] = [
  {
    id: '1',
    title: '研报自动化实战',
    description: '作为投研人，每天面对动辄几十页的 PDF 机构研报，手动摘录数据和分析逻辑总是效率极低。本期视频通过实战演示，带你打通研报自动化的“最后一公里”：我开发了一款网页自动解析插件，配合自研的 Agent（智能体）工作流，实现了从研报抓取、深度解析到核心观点提取的全自动化流程。',
    watchUrl: 'https://weixin.qq.com/sph/AOQouN7yb',
  },
];

const VideoCourses: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const courseId = searchParams.get('course');
  const selected = courseId ? COURSES.find((c) => c.id === courseId) : null;

  const openCourse = (id: string) => {
    setSearchParams({ course: id });
  };

  const backToList = () => {
    setSearchParams({});
  };

  return (
    <div className="flex-grow flex flex-col animate-fadeIn min-h-[calc(100dvh-100px)] md:min-h-[calc(100vh-140px)] pt-16 md:pt-20">
      <div className="flex justify-between items-center mb-6 md:mb-8">
        <div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Video className="text-red-500" size={28} />
            视频号课程
          </h1>
          <p className="text-gray-500 text-sm mt-1">微信扫码观看，目前仅支持移动端体验</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-3 py-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 hover:text-white text-sm transition-all"
        >
          <ArrowLeft size={18} />
          返回首页
        </button>
      </div>

      {selected ? (
        <div className="glass-morphism rounded-2xl border border-white/10 p-6 md:p-10 max-w-lg mx-auto w-full">
          <button
            onClick={backToList}
            className="flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-6 transition-colors"
          >
            <ArrowLeft size={16} />
            返回课程列表
          </button>
          <h2 className="text-lg font-bold text-white mb-2">{selected.title}</h2>
          <p className="text-gray-400 text-sm mb-8">{selected.description}</p>
          <p className="text-amber-400/90 text-xs font-medium mb-4">仅支持通过微信扫码观看</p>
          <div className="relative p-5 bg-white rounded-3xl mb-6 inline-block group">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(selected.watchUrl)}`}
              alt="微信扫码观看"
              className="w-[220px] h-[220px]"
            />
            <div className="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-white/70 backdrop-blur-[1px] rounded-3xl">
              <div className="p-2 bg-black rounded-lg mb-2">
                <User size={16} className="text-white" />
              </div>
              <p className="text-black font-bold text-xs">微信扫码观看</p>
            </div>
          </div>
          <p className="text-[10px] text-gray-500">请使用微信扫描上方二维码，在视频号中观看本课程</p>
        </div>
      ) : (
        <div className="grid gap-4 md:gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {COURSES.map((course) => (
            <button
              key={course.id}
              onClick={() => openCourse(course.id)}
              className="text-left glass-morphism rounded-2xl border border-white/10 p-6 hover:border-red-500/30 hover:bg-white/5 transition-all group"
            >
              <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center mb-4 group-hover:bg-red-500/20 transition-colors">
                <Video size={24} className="text-red-400" />
              </div>
              <h3 className="font-bold text-white mb-2 group-hover:text-red-300 transition-colors">{course.title}</h3>
              <p className="text-gray-500 text-sm line-clamp-2">{course.description}</p>
              <p className="text-[11px] text-gray-500 mt-3">微信扫码观看</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default VideoCourses;
