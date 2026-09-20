import { Mesh, Line, Points, Object3D } from 'three';

export function disposeScene(scene: Object3D) {
  scene.traverse(object => {
    if (object instanceof Mesh || object instanceof Line || object instanceof Points) {
      object.geometry.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach(material => material.dispose());
    }
  });
}
