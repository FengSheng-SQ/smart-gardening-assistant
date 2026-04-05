import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';

class LocationService {
  Future<bool> hasPermission() async {
    print('📍 [LocationService] 检查位置权限...');
    LocationPermission permission = await Geolocator.checkPermission();
    print('📍 [LocationService] 当前权限状态: $permission');

    if (permission == LocationPermission.denied) {
      print('📍 [LocationService] 权限被拒绝，请求权限...');
      permission = await Geolocator.requestPermission();
      print('📍 [LocationService] 请求权限后状态: $permission');

      if (permission == LocationPermission.denied) {
        print('❌ [LocationService] 权限仍被拒绝');
        return false;
      }
    }

    if (permission == LocationPermission.deniedForever) {
      print('❌ [LocationService] 权限被永久拒绝');
      return false;
    }

    print('✅ [LocationService] 权限检查通过');
    return true;
  }

  Future<Map<String, dynamic>> getCurrentLocation() async {
    print('📍 [LocationService] 开始获取当前位置...');

    final hasPermission = await this.hasPermission();
    if (!hasPermission) {
      throw Exception('Location permission not granted');
    }

    print('📍 [LocationService] 调用 Geolocator.getCurrentPosition...');
    final position = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );

    print('✅ [LocationService] GPS坐标获取成功:');
    print('   - 纬度: ${position.latitude}');
    print('   - 经度: ${position.longitude}');

    // 获取城市名称
    print('📍 [LocationService] 开始反向地理编码...');
    String city = 'Unknown';
    try {
      List<Placemark> placemarks = await placemarkFromCoordinates(
        position.latitude,
        position.longitude,
      );

      print('📍 [LocationService] 地理编码结果数量: ${placemarks.length}');

      if (placemarks.isNotEmpty) {
        final first = placemarks.first;
        print('📍 [LocationService] 第一个地理编码结果:');
        print('   - name: ${first.name}');
        print('   - locality: ${first.locality}');
        print('   - administrativeArea: ${first.administrativeArea}');
        print('   - subAdministrativeArea: ${first.subAdministrativeArea}');
        print('   - country: ${first.country}');

        // 多层fallback: locality -> administrativeArea -> subAdministrativeArea -> name -> ISO country code
        city = first.locality ??
               first.administrativeArea ??
               first.subAdministrativeArea ??
               first.name ??
               first.isoCountryCode ??
               'Unknown';

        print('✅ [LocationService] 确定城市: $city');
      } else {
        print('⚠️ [LocationService] 未找到地理编码结果');
      }
    } catch (e) {
      print('❌ [LocationService] 反向地理编码异常: $e');
      print('📍 [LocationService] 使用坐标作为位置标识');
    }

    final result = {
      'latitude': position.latitude,
      'longitude': position.longitude,
      'city': city,
      'source': 'gps',
    };

    print('✅ [LocationService] 返回位置信息: $result');
    return result;
  }

  Future<Map<String, dynamic>> getLocationFromCity(String city) async {
    print('📍 [LocationService] 从城市名称获取位置: $city');

    try {
      List<Location> locations = await locationFromAddress(city);
      print('📍 [LocationService] 找到 ${locations.length} 个位置结果');

      if (locations.isNotEmpty) {
        final result = {
          'latitude': locations.first.latitude,
          'longitude': locations.first.longitude,
          'city': city,
          'source': 'manual',
        };
        print('✅ [LocationService] 返回位置: $result');
        return result;
      }
    } catch (e) {
      print('❌ [LocationService] 从城市获取位置失败: $e');
    }

    // 返回默认位置（北京）
    print('📍 [LocationService] 使用默认位置（北京）');
    return {
      'latitude': 39.9042,
      'longitude': 116.4074,
      'city': city,
      'source': 'manual',
    };
  }
}
