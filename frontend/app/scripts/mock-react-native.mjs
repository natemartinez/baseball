export const Platform = {
  OS: 'web',
  select: (obj) => obj.web ?? obj.default,
};

export const StyleSheet = {
  create: (styles) => styles,
};

export const View = 'View';
export const Text = 'Text';
export const TouchableOpacity = 'TouchableOpacity';
export const ScrollView = 'ScrollView';
export const Modal = 'Modal';
export const FlatList = 'FlatList';
export const ActivityIndicator = 'ActivityIndicator';
export const useWindowDimensions = () => ({ width: 1200, height: 800 });
export const Animated = {
  Value: class {
    constructor(v) { this.val = v; }
    setValue(v) { this.val = v; }
    interpolate(cfg) { return this; }
  },
  timing: () => ({
    start: (cb) => cb && cb({ finished: true }),
  }),
};
