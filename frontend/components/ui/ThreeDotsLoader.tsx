import React from 'react';
const ThreeDotsLoader = () => {
  return (
    <div className="flex items-center space-x-1 p-2">
      <div className="w-2 h-2 rounded-full bg-blue-500 animate-[bounce_1.4s_ease-in-out_infinite] [animation-delay:-0.32s]"></div>
      <div className="w-2 h-2 rounded-full bg-blue-500 animate-[bounce_1.4s_ease-in-out_infinite] [animation-delay:-0.16s]"></div>
      <div className="w-2 h-2 rounded-full bg-blue-500 animate-[bounce_1.4s_ease-in-out_infinite] [animation-delay:-0.08s]"></div>
      <div className="w-2 h-2 rounded-full bg-blue-500 animate-[bounce_1.4s_ease-in-out_infinite]"></div>
    </div>
  );
};
// const ThreeDotsLoader: React.FC = () => {
//   return (
//     <>
//       <span className="loader"></span>
//       <style jsx>{`
//         .loader {
//           width: 12px;
//           height: 12px;
//           border-radius: 50%;
//           display: block;
//           margin: 15px auto;
//           position: relative;
//           color: black;e
//           box-sizing: border-box;
//           animation: animloader 2s linear infinite;
//         }

//         @keyframes animloader {
//           0% {
//             box-shadow: 14px 0 0 -2px, 38px 0 0 -2px, -14px 0 0 -2px, -38px 0 0 -2px;
//           }
//           25% {
//             box-shadow: 14px 0 0 -2px, 38px 0 0 -2px, -14px 0 0 -2px, -38px 0 0 2px;
//           }
//           50% {
//             box-shadow: 14px 0 0 -2px, 38px 0 0 -2px, -14px 0 0 2px, -38px 0 0 -2px;
//           }
//           75% {
//             box-shadow: 14px 0 0 2px, 38px 0 0 -2px, -14px 0 0 -2px, -38px 0 0 -2px;
//           }
//           100% {
//             box-shadow: 14px 0 0 -2px, 38px 0 0 2px, -14px 0 0 -2px, -38px 0 0 -2px;
//           }
//         }
//       `}</style>
//     </>
//   );
// };

export default ThreeDotsLoader;
