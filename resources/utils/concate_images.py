import os
import re
import cv2
import numpy as np
import yaml
import argparse

def _extract_sort_key(filename):
    """ファイル名のソートキーを生成

    パターン \d{1,2}-\d{1,2}-\d{1,2} に一致する場合は、
    各区切りを整数として比較する。
    それ以外は数字と文字列を混在させた自然順ソートキーを返す。
    """
    name, _ = os.path.splitext(filename)
    match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{1,2})$', name)
    if match:
        return (0, tuple(int(group) for group in match.groups()))

    parts = re.split(r'(\d+)', filename)
    key = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return (1, tuple(key))

def is_uniform_color(img, height, from_bottom=False, tolerance=5):
    """画像の上端または下端が指定高さ分単色かどうかをチェック
    
    Args:
        img: 画像配列
        height: チェック対象の高さ
        from_bottom: Trueなら下端、Falseなら上端をチェック
        tolerance: 色の許容差（0-255、0なら完全一致）
    """
    if img.shape[0] < height:
        return False
    if from_bottom:
        section = img[-height:, :]
    else:
        section = img[:height, :]
    
    # 最初のピクセルの色
    first_color = section[0, 0]
    
    if tolerance == 0:
        # 完全一致チェック
        return np.all(section == first_color)
    else:
        # 許容値チェック（各チャンネルが許容値以内）
        diff = np.abs(section.astype(int) - first_color.astype(int))
        return np.all(diff <= tolerance)

def should_save_image(image_height, min_height):
    """画像を保存すべきかチェック
    
    Args:
        image_height: 画像の高さ（ピクセル）
        min_height: 保存する最小高さ
    
    Returns:
        True なら保存、False なら保存しない
    """
    return image_height >= min_height

def process_images(directory_path, output_directory, separate_height, pattern_separate_height, extensions, tolerance=10, not_save_less_than_height=1):
    """画像をグループ化して結合し、さらに分割して保存"""
    extensions = tuple(f'.{ext.lower()}' for ext in extensions)
    
    try:
        image_files = sorted(
            [f for f in os.listdir(directory_path) if f.lower().endswith(extensions)],
            key=_extract_sort_key,
        )
    except FileNotFoundError:
        print(f"エラー: ディレクトリ '{directory_path}' が見つかりません。")
        return

    if not image_files:
        print("ディレクトリ内に画像ファイルが見つかりません。")
        return

    # 出力ディレクトリ作成
    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    # separated サブディレクトリ作成
    separated_dir = os.path.join(output_directory, 'separated')
    if not os.path.exists(separated_dir):
        os.makedirs(separated_dir, exist_ok=True)

    # イメージファイルリストをコンソールに出力する
    print(f"Input_imagefile_list: {image_files}")
    group_images = []
    file_counter = 1

    for filename in image_files:
        filepath = os.path.join(directory_path, filename)
        img_array = cv2.imread(filepath)
        if img_array is None:
            continue

        group_images.append(img_array)

        # 下端が単色ならグループを保存
        if is_uniform_color(img_array, separate_height, from_bottom=True):
            if group_images:
                merged_array = np.vstack(group_images)
                output_path = os.path.join(output_directory, f"{file_counter:04d}.png")
                saved = cv2.imwrite(output_path, merged_array)
                if saved:
                    print(f"グループ {file_counter} を '{os.path.abspath(output_path)}' に保存しました。({len(group_images)} 画像)")
                    # 分割処理
                    split_image(merged_array, separated_dir, file_counter, separate_height, pattern_separate_height, tolerance, not_save_less_than_height)
                else:
                    print(f"エラー: グループ {file_counter} の保存に失敗しました。")
                group_images = []
                file_counter += 1

    # 最後のグループを保存
    if group_images:
        merged_array = np.vstack(group_images)
        output_path = os.path.join(output_directory, f"{file_counter:04d}.png")
        saved = cv2.imwrite(output_path, merged_array)
        if saved:
            print(f"グループ {file_counter} を '{os.path.abspath(output_path)}' に保存しました。({len(group_images)} 画像)")
            # 分割処理
            split_image(merged_array, separated_dir, file_counter, separate_height, pattern_separate_height, tolerance, not_save_less_than_height)
        else:
            print(f"エラー: グループ {file_counter} の保存に失敗しました。")

def is_row_uniform_color(img_row, tolerance):
    """画像の1行が単色かどうかをチェック
    
    JPEG圧縮ノイズやグラデーションに強い判定。
    行内のピクセルの色の分散が小さいかをチェック。
    
    Args:
        img_row: 1行のピクセルデータ（[width, 3]）
        tolerance: 色の許容差の最大値
    """
    # 各チャンネルの最大値と最小値の差を計算
    min_vals = np.min(img_row, axis=0)
    max_vals = np.max(img_row, axis=0)
    color_range = max_vals - min_vals
    
    # すべてのチャンネルで許容値以下なら単色と判定
    return np.all(color_range <= tolerance)

def is_row_similar(row1, row2, tolerance):
    """隣接行がほぼ同じパターンかどうかをチェック"""
    diff = np.abs(row1.astype(int) - row2.astype(int))
    pattern_tolerance = int(tolerance / 2)
    return np.all(diff <= pattern_tolerance)

def is_separator_row(merged_array, y, tolerance):
    """余白候補となる行かどうかを判定"""
    height = merged_array.shape[0]
    row = merged_array[y, :]
    if is_row_uniform_color(row, tolerance):
        return 'uniform'
    if y + 1 < height and is_row_similar(row, merged_array[y + 1, :], tolerance):
        return 'pattern'
    if y > 0 and is_row_similar(row, merged_array[y - 1, :], tolerance):
        return 'pattern'
    return None

def split_image(merged_array, separated_dir, group_number, separate_height, pattern_separate_height, tolerance, not_save_less_than_height):
    """グループ化された画像を余白を除いて分割"""
    height, width = merged_array.shape[:2]
    sub_counter = 1
    y = 0
    
    while y < height:
        # 連続した余白候補行をカウント（余白をスキップ）
        uniform_count = 0
        pattern_count = 0
        temp_y = y
        while temp_y < height:
            sep_type = is_separator_row(merged_array, temp_y, tolerance)
            if sep_type == 'uniform':
                uniform_count += 1
                pattern_count = 0
            elif sep_type == 'pattern':
                pattern_count += 1
                uniform_count = 0
            else:
                break
            temp_y += 1
        
        # separate_height以上の連続単色行、またはpattern_separate_height以上の連続パターン行があれば、余白と判定
        if uniform_count >= separate_height or pattern_count >= pattern_separate_height:
            y = temp_y
            if y >= height:
                break
        else:
            # 画像部分の開始
            start_y = y
            
            # 次の連続余白候補行セクションまで進む
            while y < height:
                uniform_count = 0
                pattern_count = 0
                temp_y = y
                while temp_y < height:
                    sep_type = is_separator_row(merged_array, temp_y, tolerance)
                    if sep_type == 'uniform':
                        uniform_count += 1
                        pattern_count = 0
                    elif sep_type == 'pattern':
                        pattern_count += 1
                        uniform_count = 0
                    else:
                        break
                    temp_y += 1
                
                # separate_height以上の連続単色行、またはpattern_separate_height以上の連続パターン行があれば、分割点と判定
                if uniform_count >= separate_height or pattern_count >= pattern_separate_height:
                    break
                
                y = temp_y if temp_y > y else y + 1
            
            # 画像部分を保存
            end_y = y
            image_part = merged_array[start_y:end_y, :]
            if image_part.shape[0] > 0 and should_save_image(image_part.shape[0], not_save_less_than_height):
                output_path = os.path.join(separated_dir, f"{group_number:04d}_{sub_counter:04d}.png")
                saved = cv2.imwrite(output_path, image_part)
                if saved:
                    print(f"  分割 {sub_counter} を '{os.path.abspath(output_path)}' に保存しました。")
                else:
                    print(f"  エラー: 分割 {sub_counter} の保存に失敗しました。")
                sub_counter += 1


def collect_target_directories(input_directory, scan_subdir):
    """入力ディレクトリと必要に応じてサブディレクトリを収集する"""
    target_dirs = [input_directory]

    if not scan_subdir:
        return target_dirs

    for current_dir, dirnames, _ in os.walk(input_directory):
        rel_path = os.path.relpath(current_dir, input_directory)
        depth = 0 if rel_path in ('.', '') else len(rel_path.split(os.sep))

        if 1 <= depth <= 2:
            target_dirs.append(current_dir)

        if depth >= 2:
            dirnames[:] = []

    return target_dirs


def process_directory_tree(input_directory, output_directory, scan_subdir, separate_height, pattern_separate_height, extensions, tolerance, not_save_less_than_height):
    """入力ディレクトリ構造を保持しつつディレクトリごとに画像処理を実行する"""
    if not os.path.exists(input_directory):
        print(f"エラー: 入力ディレクトリ '{input_directory}' が見つかりません。")
        return

    target_dirs = collect_target_directories(input_directory, scan_subdir)
    for directory_path in sorted(target_dirs):
        rel_path = os.path.relpath(directory_path, input_directory)
        if rel_path in ('.', ''):
            target_output_dir = output_directory
        else:
            target_output_dir = os.path.join(output_directory, rel_path)

        print(f"処理対象ディレクトリ: {directory_path}")
        process_images(directory_path, target_output_dir, separate_height, pattern_separate_height, extensions, tolerance, not_save_less_than_height)


def main():
    parser = argparse.ArgumentParser(description='画像をグループ化して結合するスクリプト')
    parser.add_argument('config_file', help='設定ファイルのパス (YAML形式)')
    args = parser.parse_args()

    # YAML設定ファイルを読み込む
    try:
        with open(args.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"エラー: 設定ファイル '{args.config_file}' が見つかりません。")
        return
    except yaml.YAMLError as e:
        print(f"エラー: YAMLファイルの解析に失敗しました: {e}")
        return

    # 設定から値を取得
    input_directory = config.get('input_directory')
    output_directory = config.get('output_directory')
    separate_height = config.get('separate_height', 50)
    pattern_separate_height = config.get('pattern_separate_height', 3)
    extensions = config.get('extensions', [])
    tolerance = config.get('tolerance', 10)
    not_save_less_than_height = config.get('not_save_less_than_height', 1)
    scan_subdir = config.get('scan_subdir', False)

    if not input_directory or not output_directory:
        print("エラー: 設定ファイルに 'input_directory' または 'output_directory' が指定されていません。")
        return

    if not extensions:
        print("エラー: 設定ファイルに 'extensions' が指定されていません。")
        return

    # 関数を実行
    process_directory_tree(input_directory, output_directory, scan_subdir, separate_height, pattern_separate_height, extensions, tolerance, not_save_less_than_height)

if __name__ == '__main__':
    main()