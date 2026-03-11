export interface Shot {
  id: number;
  duration: string;
  durationSeconds: number;
  previewImage: string;
  sceneDescription: string;
  voiceover: {
    role: string;
    roleTag: string;
    text: string;
    charRange: string;
  };
  shotDescription: {
    tags: string[];
    text: string;
  };
  cameraMovement: string;
  timelineFrames?: ShotFrame[];
  timelineImages: string[];
  timelineWidth: string;
}

export interface ShotFrame {
  id: string;
  type: 'start' | 'key' | 'end';
  imageUrl: string;
  label: string;
}

export const shots: Shot[] = [
  {
    id: 1,
    duration: '7.8s',
    durationSeconds: 7.8,
    previewImage: '/image/k1.jpeg',
    sceneDescription: '展示武当山巅金殿全貌，张三丰与张无忌在金殿前对峙',
    voiceover: {
      role: '旁白',
      roleTag: 'R0',
      text: '元朝末年，武当与明教因正邪之辩，在武当山巅展开巅峰对决！',
      charRange: '19-27',
    },
    shotDescription: {
      tags: ['太极剑 (P1)', '明教令牌 (P2)', '张三丰 (R1)', '张无忌 (R2)'],
      text: '日漫电影质感，全景，俯拍视角，武当金殿（纯铜鎏金金殿在阳光下闪耀，云海环绕山脚，七十二峰如莲瓣舒展）。画面中央金殿前，图[3]的青袍老道持图[1]的银白太极剑立于左侧，图[4]的红衣青年手握图[2]的红色明教令牌站在右侧，两人呈对峙姿态。',
    },
    cameraMovement: '固定全景运镜，无明显移动，保持青袍老道与红衣青年的对峙状态。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuDZlNxi2SM48KSuX4uSgpJtPPlsNOxjazlFY2fkslFCCeUo3jCX_ITuPMO9DOKOsoHMbZxYj14MCp0Vhkuk_uZJ44YVPTnuuKwJ_IeIS2rMKHv3pcZ0LU_P7BGLHC0FaNJs345oWh1lRM3EVcAvkwbVb7uyKKT47mCSSIcB9Cpu-UUhHIlJOjhzgmGC51wz-LUx72m1qiI2Z3Wof4XB4SIpyenDpbSn2i8DLpY-9wOqkhBiUdN7MS6elVb95SVLxVN7Wxh4_hY77DLT',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuDoqLri8c4EVus46ChJ6Gwqj6ZxzUWyDPMhp4MKXS6H7KvqROG1y4GNhTvjP_XX-EQQJ3AbUFRJ-A3BQxlE-8IDv9x35nqQP0kydYRADkxW0khaV7eYrKI4Dabr44s5s-wTuEexcoh4oNvu0Z3jbxu_7TMgoubYr__ZaRnzOqN4ywy3j_cjx1HaoBYuQnhKv9dbDjOKClLecAWtSZHpRjhokrlAqEKvyGqhS4Vks3PuSVESf1jHqkX58xzVkL_wLKD00dOvj8A0eFrF',
    ],
    timelineWidth: '360px',
  },
  {
    id: 2,
    duration: '3.0s',
    durationSeconds: 3.0,
    previewImage: '/image/k2.jpeg',
    sceneDescription: '张三丰运气凝神，太极剑气场初现',
    voiceover: {
      role: '张三丰',
      roleTag: 'R1',
      text: '无忌，你当真要与武当为敌？',
      charRange: '10-15',
    },
    shotDescription: {
      tags: ['太极剑 (P1)', '张三丰 (R1)'],
      text: '中景，正面视角，张三丰手持太极剑缓缓抬起，剑身泛起淡蓝色气场，周围空气出现波纹扭曲效果，青袍衣袂无风自动。',
    },
    cameraMovement: '缓慢推进，从中景推至近景，聚焦张三丰面部与太极剑。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuCLcTsEi8t5vGWXLsuCSc3adSbzEEO-30sXMVMxSx7063LtZdN_jlS3-c6Z4cdPSt8SsIyYYDpAIm8m90oW-UjyJWXfKRocZRhsNblrixE07bFEFjxhummc0zHTdZnpGhY2ESaiZSHlj9EDqYeHO3zMCk5fxU7x_xjQBNIgoErCky9AnlMtzYZEfKnJE7ay8-5ExyfNDEOlr8hjLtGs3RZUwE0xhK5RReOYaONQHFqIiDO7zDLhwsaxUzwn3dQjYpAZKcq6p_GZiOBH',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuDe0s5MYOQgFB0ib4RdGE8RtNEFFJRhsvcKaWQLcmFppHjgRo5RLUstG221OMgUreIzSyYifvmODMIWiw6GJZx5UjEORUQ5ihZQ3jpKd4XnrMnp-PbLgJLuAFVgTRnaZiUKRVuJiQvpRs7z4hNOwGZXxzGgiHABdQDHaLNWfmRZVcdOqNVMrSSZdx43A9bnCEfkt7gvK2Mr-EtIKvUNjIc_QwQdj2QXG88A59bdXsgJ7TNjzAkAnjmYQb6xBey0_TY__hVNRP7ytP1w',
    ],
    timelineWidth: '140px',
  },
  {
    id: 3,
    duration: '3.0s',
    durationSeconds: 3.0,
    previewImage: '/image/k3.jpeg',
    sceneDescription: '张无忌展示明教令牌，明教弟子列阵于后',
    voiceover: {
      role: '张无忌',
      roleTag: 'R2',
      text: '太师父，无忌别无选择，只能一战！',
      charRange: '12-18',
    },
    shotDescription: {
      tags: ['明教令牌 (P2)', '张无忌 (R2)'],
      text: '中景，侧面视角，张无忌举起明教令牌，令牌发出红色光芒。身后明教弟子整齐列阵，旗帜飘扬。',
    },
    cameraMovement: '环绕运镜，从张无忌正面旋转至侧面，展示身后明教阵势。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuCGle-IcmzaIwjNnV5cR0wx5P3_BpsjhUSQZx824ysXZ7qqB9bZYBI_zf771wl7ok8n7-JvARLj6GjYnZ2luW8PAXNhlx5hKdUkg8c2tXUruFdBKDhP8Ge2P7YbZE0ElTs_xAGLTFLOyddv53sEUYm6BDJkgPenX0UKfx9tSB6JqMsRhaXueN31PKDAYUUg8fBQQnWIxIUZbqYqvGUbGoXsSD4JglmMb-WMTlr1HMRTg92uwUFREuu2heXNO4DH8cW_d0K3olCvWqgz',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuBOF5yjnjgzb_uH3K7pBCVMSI6JJbRx_nfX-q00QmAo_43HLm8UjFEyZ5feJBdKOAmLhwjeE3viUdSymG6n83QhYhje7yDXKH06vmqy7FM_ahhkU7auMMJJN2vzhrWDHvri2EkorBeY7O0XIFTJsGFxzKfoTpW1QQCuPsh8CGWhUyq6EIMxWixgrcLwN0EZVl24hwtG6yXZohBR_ir4jZDj1vwgYMNlRfaYPAJ5W4azZXdOjBHfPkcrb9Pjp7WTKYFphxR25OttG7lp',
    ],
    timelineWidth: '140px',
  },
  {
    id: 4,
    duration: '2.5s',
    durationSeconds: 2.5,
    previewImage: '/image/k4.jpeg',
    sceneDescription: '双方交锋，太极剑与明教令牌碰撞产生能量冲击',
    voiceover: {
      role: '旁白',
      roleTag: 'R0',
      text: '两大绝世高手，终于正面交锋！',
      charRange: '10-14',
    },
    shotDescription: {
      tags: ['太极剑 (P1)', '明教令牌 (P2)', '张三丰 (R1)', '张无忌 (R2)'],
      text: '特写，正面对冲视角，太极剑的蓝色剑气与明教令牌的红色火焰在画面中央剧烈碰撞，产生白色能量冲击波，地面碎裂。',
    },
    cameraMovement: '快速推进至碰撞点，随后震荡拉远展现冲击波范围。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuAyKtB9VZOBYxUQMj-6iwfbSyt3H0YcViH7WLgaTimC1prGQpfFwzPJjRmljSy_iNnr8aNCJIKuQ2rQHtNn96rWUZdOtcawXnD4toI6G3g-t89GDxrEUlzx9zE9XZx0MwqO7W8t61tSGp-LoY95TWPTSlIAHy4KRmcCMVhZHrAmesDiZwqUrVTzIHHnwHWZbDdNZugzhKtM5QuOS_8Ei15MVSL6SF_2T3tdgX1ME4d-fTEJTLTTbMkJz-h0H6IMS9fhDKN6QYCDBt5y',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuD4ZlDmfdAYTnErddN-3z9MPr2pe4D56RumOWqNWgTcslBbbev9IzeH0bYaVWo__uQmk82UvFNSMwsLUXuOKSr3YrHchVjeb1rHyB1wTbaLmpB9NZLKckhyQiBLzlsHxiahzyEw-lXERH8uy4s9L-MXWjVXBeBWh8xtZe6db99wb6W53r5QM99pNpXM1nF8puT2ZQIccBXCeQaNESg0mxwF8TFA3MMYYeoVvlBHFLtnOOzV-uhlLax07LWXonZ78mngeQTTp7oDTahd',
    ],
    timelineWidth: '120px',
  },
  {
    id: 5,
    duration: '5.4s',
    durationSeconds: 5.4,
    previewImage: '/image/k5.jpeg',
    sceneDescription: '张三丰施展太极剑法，剑招绵延不绝',
    voiceover: {
      role: '张三丰',
      roleTag: 'R1',
      text: '看清楚了，这就是太极剑法的精髓——以柔克刚，四两拨千斤！',
      charRange: '22-30',
    },
    shotDescription: {
      tags: ['太极剑 (P1)', '张三丰 (R1)'],
      text: '全景，跟拍视角，张三丰在金殿前舞剑，太极剑划出一道道弧形轨迹，形成太极图案。剑招流畅如水，气场如涟漪般向外扩散。',
    },
    cameraMovement: '360度环绕跟拍，配合剑招节奏加速与减速。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuDGRUIkyrP5ajy6Ia1Xfrsn53-sXAOQm06DVIC9wFIukcpnE5-m08cu2q7KIIITSwi_8sNUZu0n0rhvoVboUtDb2PN7GD-9dsiVsIewrObx3-pm-diCoM-qYUogpgZ2XJ0rHJHJGxsaGvDYyhDggQgMSRk3Kq0mt5bEo2Ruu4rugSOmxksNrLLw8xAzvEJgwGrvHGiMjNYRZke2TTPrEgnKvxfuN6a8RuRIw1L-5P6Whb6BQMD2fz6-ixInamrwgcOCVn73GOqP9i9I',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuAhJG64Cug6bDYxiovkR_JGU48iWFtSzYNgMGxYRdic0Kt7ukaAOAd0IM--wAkRiqBpKEXvK63EHSfikdKXUEANpGxDJlgc7vvb_LG7ZSLDTBVa0-tzBrHOYBVMjn5rxHwJuRb6Wz10j6GwzwDBawNAJ4vndr6srQKNqPNZrQXuQ1RUU1RMgWV31BnMLJYll7d9Hk5As51GLmS9Zkf_Mbu8DzoK8x7B5oxr7BzU4Mmd5vKBYH7At86T7driyj6KNj98d5M55Hg2Ysaq',
    ],
    timelineWidth: '240px',
  },
  {
    id: 6,
    duration: '2.0s',
    durationSeconds: 2.0,
    previewImage: '/image/k6.png',
    sceneDescription: '张无忌以乾坤大挪移化解攻势',
    voiceover: {
      role: '张无忌',
      roleTag: 'R2',
      text: '乾坤大挪移！',
      charRange: '5-8',
    },
    shotDescription: {
      tags: ['张无忌 (R2)'],
      text: '近景，仰拍视角，张无忌双掌推出，空气中出现红色能量漩涡，将太极剑气反弹回去。',
    },
    cameraMovement: '快速仰拍推近，聚焦张无忌双掌与能量漩涡。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuAzpuupKGLz-5AuF7OfdHBNjkN9UGzrSBiatfHwQFfZZrU4ZQD1LC4qppZjH9dw7XDOvNR7TBbq_9f2yVTv3ipUqITfRmPvjivQ1EjY1PO7hRr8Kz4ttuoY2MgA_SeRBFZCyuR0jSTw6ryBicSWkLkgdGROUN_yEqrYHKfpK-VK8tKa9-O0YaM7y-DhQocqxV8djU0jG-Q90XrgBbtGnCEh3r5HYA03ZOMqo9yU5RU_c_rN5B90EEkdv-bIkmG25nt-PjGpCSpCjm3Q',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuACZv9is6855xNyK6fBT5RpmBxuCjQeCc7jRw3aR1Xr5eiMGMjxf85tm2zZKxsKLfStk7uxDuS8u8-KusKkLbUJXYgXE3dV8Smh0CKskqayrlTX4vgnEAGR5zhIjQAV5V9wDFP0ekmEB4F1BN0zNsHWiO_ayJIaElMPV3HTVorpOU8Z5CBi_jRQLZSAOvgU367FUGDXhsOhle4c9I6wQhPCGfWar_0JIi7Qsjce6W3QvbcfembS-WwBPoNT1bhYhYpPOuZ9_MvW9kqn',
    ],
    timelineWidth: '100px',
  },
  {
    id: 7,
    duration: '2.5s',
    durationSeconds: 2.5,
    previewImage: '/image/k7.jpeg',
    sceneDescription: '双方同时后退，短暂对峙，互相审视',
    voiceover: {
      role: '旁白',
      roleTag: 'R0',
      text: '一招之间，胜负难分。',
      charRange: '8-12',
    },
    shotDescription: {
      tags: ['张三丰 (R1)', '张无忌 (R2)'],
      text: '全景，平视视角，两人各退数步，衣袂飘动，尘土缓缓落下。双方目光如电，互相对视。',
    },
    cameraMovement: '固定镜头，保持双方均在画面中，微微推进。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuBsaplIc0OAktrEVTMa2Fib2fDqxkzZ8iDJ_nFLV1aMkGP_44AAYy-22TLgRSLxPZ6r7SquzrYywkndiMyZMHJSeT7YQ9fOUrjd6HU9qVVjLC7lC8BJmQmVtssef18sI3-Q_s7tEGHoDKb4vlY7utmBajWkOQ-2vWoT_HKvu1DN-5MGR1UQY263ykvE-BoB9lDo8vxRM3-XjDenPX4WoscQ_nfJT_dcnRiC1-ICi6hyqJoNzjAu8Xoo-eh68ULkKFSjaKMziR_Wbfzf',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuD7hHywQYzB5L0wW66CHZFUx72boqYSDeUT1QF0rwVIk4oTfl-jhcQM3Mb6Uvbi7MCY5LfZtAMtoAWOfJXcSYv5eJhqWHLTDawgeXvVBXFaOA0V7RiuMuyQgaIKKLU4KdLsPPo41ySAQ3rYTbvL8ufR2boKOtsOeokUWUkTjHTdF-6NVxQxROT9sLHbBQfbmn5_tQKgbisR2wq6Hi3jhnY205xuSqiiJ2mxTLFaxwGVowHovgSP8T-J6XTXb9iX0Qt08cAfCdPQbCq0',
    ],
    timelineWidth: '120px',
  },
  {
    id: 8,
    duration: '3.0s',
    durationSeconds: 3.0,
    previewImage: '/image/k8.jpeg',
    sceneDescription: '最终一击，两人各出绝招，能量爆发笼罩金殿',
    voiceover: {
      role: '旁白',
      roleTag: 'R0',
      text: '这一战，注定载入武林史册！',
      charRange: '10-14',
    },
    shotDescription: {
      tags: ['太极剑 (P1)', '明教令牌 (P2)', '张三丰 (R1)', '张无忌 (R2)'],
      text: '远景，俯拍视角，两人同时冲向对方，蓝色与红色能量在画面中央汇聚爆发，光芒笼罩整座金殿，云海被冲击波吹散。',
    },
    cameraMovement: '快速拉远至大全景，展现能量爆发的宏大场面。',
    timelineImages: [
      'https://lh3.googleusercontent.com/aida-public/AB6AXuDF8W1XvTlw7c8ICzaagk_8ySjPM10-uKZiOFVsXMB3myQ7YUbmtybGb1OvfS1r15CRZslqzQaCDTMRHhEjOdZsRKOFhzL0c9Jqks4AU6dCx42JrhpmiIVvE4DswDPY_rg46kqvSu5jr9Dtx38dAomXS6jK5fDhJt0a4hzSHzdvks6cNudoD52GkACO4G41ia9kYFOo4lTqS_8P9GQjYr8FPsqP8x_loRv_pk9XG_PtsAcNPCbUECV_3jG4m40C_zaJzyzzLydhvJvE',
      'https://lh3.googleusercontent.com/aida-public/AB6AXuB7w_HHWnOJRJXTKnPxKs1N3BA4IojsUzkI4J6iHLJT2ZcH-cVNPj164G5OtS4i1MUoALVtFljGPy6cNTlV2zh-BNajF3ZlDKpEX0Dq-SBnEXEvBAcytU5FNUDUrwwtad5ZO8kE2M7baW4VEdnrgP2K85CVhqbA-JD_0Ykp5vt1XPMChX8kBRWGa52PxZzRLL1UA9VX3xQVWqpwOXjjX6zcFF0OnjfYjUQh-BUHWaXoBUBw5opmEdHTsdeW2E5WIQF3X6mLERcpGQjT',
    ],
    timelineWidth: '140px',
  },
];

export function getTotalDuration(): string {
  const total = shots.reduce((sum, s) => sum + s.durationSeconds, 0);
  return `${total.toFixed(1)}s`;
}
