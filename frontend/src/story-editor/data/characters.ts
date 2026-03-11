export interface Character {
  id: string;
  name: string;
  voice: string;
  appearance: string | null;
  image: string | null;
  readonly: boolean;
}

export const characters: Character[] = [
  {
    id: 'R0',
    name: '旁白',
    voice: '男性，成年，语调浑厚，音高适中，语速沉稳，情绪激昂，无口音',
    appearance: null,
    image: null,
    readonly: true,
  },
  {
    id: 'R1',
    name: '张三丰',
    voice: '男性，老年，语调沉稳，音高适中，语速缓慢，情绪平和，无口音',
    appearance: '男性，百岁，灰白色长发束于道冠，面容清瘦，肤色白皙，汉族，五官端正，眼神平和深邃，',
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDBnbBqsh-ZR1b6wWJaZlxWLuB8q6BiB5i7E0SP0HxwSoiQ7JnsDwDqNYWmZKPWJumdwElBHovR3vCHNRtXb87tKpK3mQcCxSpmLiYrFKYYc3qu9HE9cEJEhQjzdizyktpB-NxjtcZebWL5-SlbA76AruQBmATrV3Xo0PgqmSVr2W2zzTzv0OP-2w1W9o4xAlc7NHeoaI3rTFwAETQ5gFIbBCR438fLTszD65sSXn_sMB82Cl0WkFfwkIqI8IGWDmku0oB-wPl2xdoX',
    readonly: false,
  },
  {
    id: 'R2',
    name: '张无忌',
    voice: '男性，青年，语调坚定，音高较高，语速中等，情绪激昂，无口音',
    appearance: '男性，二十岁，黑色长发披肩，面容俊朗，肤色健康，汉族，五官英气，眼神锐利，身着明教红',
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD44qsNZJzttcRQD0fuFgCAQxtSTVbTUuIOelcb0CBKjQDDlDbNcyXkVHeEgjJvy3T0uPp0jIVJBS_UrN-eqAKi-_GJeNxoP-jKwdu2MVrQ70YP9LmpWHWFidDUPh558AiPqfx4860CECOs9noBRvWoIrNFtRV2Yu2eYPD8x6sssYZBdLkYaWu7dtZ04zTONyyByQqD70Zot63yLNXVEEo_leLdLGC6mSNti6YlhBlMTQqn_eK0C7NvHRbQPvsncs2WljkYPJ6tBqVC',
    readonly: false,
  },
  {
    id: 'R3',
    name: '赵敏',
    voice: '女性，青年，语调机灵，音高清脆，语速稍快，情绪自信，带有一丝傲气',
    appearance: '女性，十八岁，长发束起男装打扮，面容艳丽，肤色胜雪，蒙古族，五官精致，手持折扇，眼神灵动。',
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBgOwkKl91pDjpcwcX7XMfaypDtlmws9ukYrvzTISSZNWwrL9tFaReojksLEK8EtdztprHprajfkuiP97qGvNsq7ipMGpNyWbuVg0uiyYoilkQZs3e9vHGhiXd4FM4aCkL3jIbth6Becse2r8UCquw_GfJsty3Kk3V2RVon1lPbOk-OQAYJ74aLXQB1J35Bl_0c76114Mo4qFDYVlmU9Y74c7xwKnqd3LzgPF0BnWxsAVoteRmlxkhqKtFlcmA91njRydDxfFeFUVDU',
    readonly: false,
  },
];
