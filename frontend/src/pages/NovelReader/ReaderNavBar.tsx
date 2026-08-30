import cx from 'classnames';
import styles from './ReaderNavBar.module.scss';

import { store } from '@/store';
import { Reader } from '@/store/_reader';
import type { ReadChapter } from '@/types';
import {
  BorderOutlined,
  CaretDownOutlined,
  LeftOutlined,
  MinusOutlined,
  PlusOutlined,
  RightOutlined,
  SoundOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
} from '@ant-design/icons';
import { Flex, Grid } from 'antd';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { ReaderContentsButton } from './ReaderContentsButton';
import { ReaderSettingsButton } from './ReaderSettingsButton';
import { focusReaderPosition } from './utils';

export const ReaderNavBar: React.FC<{
  data: ReadChapter;
}> = ({ data }) => {
  const navigate = useNavigate();
  const { md } = Grid.useBreakpoint();
  const theme = useSelector(Reader.select.theme);
  const speaking = useSelector(Reader.select.speaking);
  const position = useSelector(Reader.select.speakPosition);
  const fontSize = useSelector(Reader.select.fontSize);
  const autoScroll = useSelector(Reader.select.autoScroll);

  const decreaseFontSize = () => {
    store.dispatch(Reader.action.setFontSize(fontSize - 1));
  };

  const increaseFontSize = () => {
    store.dispatch(Reader.action.setFontSize(fontSize + 1));
  };

  const goPrevious = () => {
    if (data.previous_id) {
      navigate(`/read/${data.previous_id}`);
    }
  };

  const goNext = () => {
    if (data.next_id) {
      navigate(`/read/${data.next_id}`);
    }
  };

  const startSpeaking = () => {
    // 朗读与自动滚动互斥：开朗读先关滚动
    store.dispatch(Reader.action.setAutoScroll(false));
    store.dispatch(Reader.action.setSpeaking(true));
    focusReaderPosition(Reader.select.speakPosition(store.getState()));
  };

  const stopSpeaking = () => {
    store.dispatch(Reader.action.setSpeaking(false));
  };

  const moveBackward = () => {
    if (position === 0) {
      if (data.previous_id) {
        navigate(`/read/${data.previous_id}`);
      }
    } else {
      store.dispatch(Reader.action.setSepakPosition(position - 1));
      focusReaderPosition(position - 1);
    }
  };

  const moveForward = () => {
    store.dispatch(Reader.action.setSepakPosition(position + 1));
    focusReaderPosition(position + 1);
  };

  const handleActionKeyDown =
    (action: () => void) => (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        action();
      }
    };

  return (
    <Flex
      align="center"
      justify="center"
      className={cx(styles.readerNavBar, {
        [styles.mobile]: !md,
      })}
      style={{
        top: 0,
        color: theme.color,
        background: md ? theme.background : theme.background + 'e5',
      }}
    >
      <div
        aria-disabled={!data.previous_id}
        aria-label="上一章"
        role="button"
        tabIndex={data.previous_id ? 0 : -1}
        onClick={goPrevious}
        onKeyDown={handleActionKeyDown(goPrevious)}
        className={cx(styles.item, {
          [styles.disabled]: !data.previous_id,
        })}
      >
        <LeftOutlined />
        {md && ' 上一章'}
      </div>

      <div
        aria-label="减小字号"
        role="button"
        tabIndex={0}
        onClick={decreaseFontSize}
        onKeyDown={handleActionKeyDown(decreaseFontSize)}
        className={styles.item}
      >
        <MinusOutlined />
      </div>

      <div
        aria-label="增大字号"
        role="button"
        tabIndex={0}
        onClick={increaseFontSize}
        onKeyDown={handleActionKeyDown(increaseFontSize)}
        className={styles.item}
      >
        <PlusOutlined />
      </div>

      <div
        aria-label="自动滚动"
        role="button"
        tabIndex={speaking ? -1 : 0}
        aria-disabled={speaking}
        onClick={() => {
          if (!speaking) {
            store.dispatch(Reader.action.setAutoScroll(!autoScroll));
          }
        }}
        onKeyDown={handleActionKeyDown(() => {
          if (!speaking) {
            store.dispatch(Reader.action.setAutoScroll(!autoScroll));
          }
        })}
        className={cx(styles.item, { [styles.disabled]: speaking })}
      >
        <CaretDownOutlined />
        {md && ' 滚动'}
      </div>

      {data.content &&
        (speaking ? (
          <>
            <div
              aria-label="上一段"
              role="button"
              tabIndex={0}
              onClick={moveBackward}
              onKeyDown={handleActionKeyDown(moveBackward)}
              className={styles.item}
            >
              <StepBackwardOutlined />
              {md && '上一段'}
            </div>
            <div
              aria-label="停止朗读"
              role="button"
              tabIndex={0}
              className={styles.item}
              onClick={stopSpeaking}
              onKeyDown={handleActionKeyDown(stopSpeaking)}
            >
              <BorderOutlined />
              {md && '停止'}
            </div>
            <div
              aria-label="下一段"
              role="button"
              tabIndex={0}
              className={styles.item}
              onClick={moveForward}
              onKeyDown={handleActionKeyDown(moveForward)}
            >
              <StepForwardOutlined />
              {md && '下一段'}
            </div>
          </>
        ) : (
          <div
            aria-label="朗读"
            role="button"
            tabIndex={0}
            className={styles.item}
            onClick={startSpeaking}
            onKeyDown={handleActionKeyDown(startSpeaking)}
          >
            <SoundOutlined />
            {md && '朗读'}
          </div>
        ))}

      <ReaderContentsButton
        className={cx(styles.item, styles.contentsButton)}
        novelId={data.novel.id}
      />
      <ReaderSettingsButton aria-label="阅读设置" className={styles.item} />

      <div
        aria-disabled={!data.next_id}
        aria-label="下一章"
        role="button"
        tabIndex={data.next_id ? 0 : -1}
        onClick={goNext}
        onKeyDown={handleActionKeyDown(goNext)}
        className={cx(styles.item, {
          [styles.disabled]: !data.next_id,
        })}
      >
        {md && '下一章 '}
        <RightOutlined />
      </div>
    </Flex>
  );
};
